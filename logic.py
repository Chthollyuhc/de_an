"""
logic.py - Toàn bộ logic nghiệp vụ tài chính
Dự án: Hệ thống Quản lý và Phân tích Danh mục Đầu tư Chứng khoán Cá nhân
Sinh viên: Trần Minh Khánh - NEU

Các hàm chính:
  - lay_gia_hien_tai()   : Gọi API vnstock lấy giá realtime
  - xu_ly_mua_co_phieu() : Logic mua, tính DCA
  - xu_ly_ban_co_phieu() : Logic bán, tính Realized P&L
  - tinh_toan_lai_lo()   : Tính trạng thái toàn danh mục
  - lay_lich_su_giao_dich(): Lấy sao kê dòng tiền
"""

import sqlite3


# ==============================================================
# HÀM LẤY GIÁ REALTIME (KHÔNG CHỈNH SỬA - ĐANG HOẠT ĐỘNG ỔN)
# ==============================================================

def lay_gia_hien_tai(ma_cp):
    """
    Lấy giá thị trường thời gian thực của cổ phiếu từ sàn Việt Nam.
    Sử dụng thư viện vnstock phiên bản API 4.x (nguồn VCI).
    """
    try:
        from vnstock.api.trading import Trading
        trading = Trading(source='VCI')
        df = trading.price_board([ma_cp])

        if 'matchPrice' in df.columns:
            gia_hien_tai = df['matchPrice'].values[0]
        elif 'Khớp lệnh - Giá' in df.columns:
            gia_hien_tai = df['Khớp lệnh - Giá'].values[0]
        else:
            gia_hien_tai = df.iloc[0, 1]

        gia_hien_tai = float(gia_hien_tai)

        # BẢN VÁ LỖI LOGIC:
        # vnstock đôi khi trả về giá dạng rút gọn (VD: 14.75 thay vì 14750)
        # Nếu giá < 1000 → đang ở dạng rút gọn → nhân 1000 để ra VNĐ thực
        # Nếu giá >= 1000 → đã ở dạng đầy đủ → giữ nguyên
        if gia_hien_tai < 1000:
            return gia_hien_tai * 1000
        return gia_hien_tai

    except Exception as e:
        print(f"⚠️ Lỗi lấy giá mã {ma_cp}: {e}")
        return 0.0


# ==============================================================
# HÀM XỬ LÝ LỆNH MUA (Tính giá vốn trung bình - DCA)
# ==============================================================

def xu_ly_mua_co_phieu(cursor, ma_nguoi_dung, ma_cp, gia_khop, khoi_luong):
    """
    Xử lý lệnh MUA cổ phiếu:
    1. Tính giá vốn trung bình mới (công thức DCA)
    2. Cập nhật bảng DANHMUC
    3. Ghi nhận vào GIAODICH
    4. Trừ tiền mặt của người dùng

    Công thức DCA (Dollar-Cost Averaging):
        GiaVonMoi = (SoLuongCu * GiaVonCu + SoLuongMua * GiaMua) / (SoLuongCu + SoLuongMua)
    """
    thanh_tien = gia_khop * khoi_luong

    # Kiểm tra xem đã có mã CP này trong danh mục chưa
    cursor.execute(
        "SELECT MaDanhMuc, SoLuongHienTai, GiaVon FROM DANHMUC WHERE MaNguoiDung = ? AND MaCoPhieu = ?",
        (ma_nguoi_dung, ma_cp)
    )
    dong_hien_tai = cursor.fetchone()

    if dong_hien_tai:
        # --- TRƯỜNG HỢP: ĐÃ CÓ MÃ NÀY → MUA THÊM (tính lại giá vốn TB) ---
        ma_danh_muc, so_luong_cu, gia_von_cu = dong_hien_tai

        so_luong_moi = so_luong_cu + khoi_luong

        # Công thức tính giá vốn trung bình (DCA):
        # Tổng tiền đã đầu tư = tiền cũ + tiền mua thêm lần này
        # Chia cho tổng số lượng mới để ra giá vốn trung bình mới
        gia_von_moi = (so_luong_cu * gia_von_cu + khoi_luong * gia_khop) / so_luong_moi

        cursor.execute(
            "UPDATE DANHMUC SET SoLuongHienTai = ?, GiaVon = ? WHERE MaDanhMuc = ?",
            (so_luong_moi, gia_von_moi, ma_danh_muc)
        )
    else:
        # --- TRƯỜNG HỢP: CHƯA CÓ MÃ NÀY → MUA LẦN ĐẦU ---
        # Giá vốn = đúng bằng giá mua lần đầu
        cursor.execute(
            "INSERT INTO DANHMUC (MaNguoiDung, MaCoPhieu, SoLuongHienTai, GiaVon) VALUES (?, ?, ?, ?)",
            (ma_nguoi_dung, ma_cp, khoi_luong, gia_khop)
        )

    # Ghi vào lịch sử GIAODICH (LaiLoChot = NULL vì đây là lệnh MUA)
    cursor.execute(
        """INSERT INTO GIAODICH (MaNguoiDung, MaCoPhieu, LoaiGiaoDich, GiaKhop, KhoiLuong, ThanhTien, LaiLoChot)
           VALUES (?, ?, 'MUA', ?, ?, ?, NULL)""",
        (ma_nguoi_dung, ma_cp, gia_khop, khoi_luong, thanh_tien)
    )

    # Trừ tiền mặt (mua thì tiêu tiền)
    cursor.execute(
        "UPDATE NGUOIDUNG SET TienMat = TienMat - ? WHERE MaNguoiDung = ?",
        (thanh_tien, ma_nguoi_dung)
    )


# ==============================================================
# HÀM XỬ LÝ LỆNH BÁN (Tính Realized P&L - Lãi/Lỗ Đã Chốt)
# ==============================================================

def xu_ly_ban_co_phieu(cursor, ma_nguoi_dung, ma_cp, gia_ban, khoi_luong):
    """
    Xử lý lệnh BÁN cổ phiếu:
    1. Kiểm tra số lượng có đủ để bán không
    2. Tính Realized P&L (Lãi/Lỗ đã chốt)
    3. Cập nhật bảng DANHMUC (giảm số lượng, GIA VỐN KHÔNG ĐỔI)
    4. Ghi vào GIAODICH với LaiLoChot
    5. Cộng tiền mặt và cập nhật TongLaiLoChot

    Công thức Realized P&L:
        LaiLoChot = (GiaBan - GiaVonTrungBinh) × SoLuongBan
        → Dương (+) = Lãi    → Âm (-) = Lỗ

    ⚠️ NGUYÊN TẮC QUAN TRỌNG:
        Khi BÁN, giá vốn trung bình KHÔNG thay đổi.
        Chỉ giảm số lượng, giữ nguyên GiaVon.
        (Khác với MUA mới làm thay đổi GiaVon)

    Trả về: (True, lai_lo_chot) nếu thành công
            (False, thông_báo_lỗi) nếu thất bại
    """
    # Kiểm tra xem có mã CP này trong danh mục không
    cursor.execute(
        "SELECT MaDanhMuc, SoLuongHienTai, GiaVon FROM DANHMUC WHERE MaNguoiDung = ? AND MaCoPhieu = ?",
        (ma_nguoi_dung, ma_cp)
    )
    dong_hien_tai = cursor.fetchone()

    # Bẫy lỗi 1: Không có mã CP này trong danh mục
    if not dong_hien_tai:
        return False, f"Bạn không có mã '{ma_cp}' trong danh mục!"

    ma_danh_muc, so_luong_hien_tai, gia_von_trung_binh = dong_hien_tai

    # Bẫy lỗi 2: Số lượng muốn bán vượt quá số đang giữ (bán khống)
    if khoi_luong > so_luong_hien_tai:
        return False, (
            f"Số lượng bán ({khoi_luong:,}) vượt quá số đang giữ ({so_luong_hien_tai:,}) "
            f"của mã '{ma_cp}'!"
        )

    # -------------------------------------------------------
    # TÍNH REALIZED P&L (LÃI/LỖ ĐÃ CHỐT)
    # -------------------------------------------------------
    # Lợi nhuận/Lỗ trên mỗi cổ phiếu = Giá bán - Giá vốn trung bình
    # Tổng lãi/lỗ = (Giá bán - Giá vốn TB) × Số lượng bán
    lai_lo_chot = (gia_ban - gia_von_trung_binh) * khoi_luong
    thanh_tien_ban = gia_ban * khoi_luong

    # Cập nhật số lượng còn lại trong DANHMUC
    so_luong_con_lai = so_luong_hien_tai - khoi_luong

    if so_luong_con_lai == 0:
        # Bán SẠCH toàn bộ: xóa mã này khỏi danh mục đang giữ
        cursor.execute("DELETE FROM DANHMUC WHERE MaDanhMuc = ?", (ma_danh_muc,))
    else:
        # Bán MỘT PHẦN: chỉ giảm số lượng, GIA VỐN KHÔNG ĐỔI
        # (đây là điểm khác biệt quan trọng với lệnh MUA)
        cursor.execute(
            "UPDATE DANHMUC SET SoLuongHienTai = ? WHERE MaDanhMuc = ?",
            (so_luong_con_lai, ma_danh_muc)
        )

    # Ghi vào lịch sử GIAODICH (lưu LaiLoChot để tra cứu sau)
    cursor.execute(
        """INSERT INTO GIAODICH (MaNguoiDung, MaCoPhieu, LoaiGiaoDich, GiaKhop, KhoiLuong, ThanhTien, LaiLoChot)
           VALUES (?, ?, 'BAN', ?, ?, ?, ?)""",
        (ma_nguoi_dung, ma_cp, gia_ban, khoi_luong, thanh_tien_ban, lai_lo_chot)
    )

    # Cộng tiền mặt thu về từ việc bán + Tích lũy vào TongLaiLoChot
    cursor.execute(
        "UPDATE NGUOIDUNG SET TienMat = TienMat + ?, TongLaiLoChot = TongLaiLoChot + ? WHERE MaNguoiDung = ?",
        (thanh_tien_ban, lai_lo_chot, ma_nguoi_dung)
    )

    return True, lai_lo_chot


# ==============================================================
# HÀM TÍNH TOÁN TRẠNG THÁI TOÀN DANH MỤC (Unrealized P&L)
# ==============================================================

def tinh_toan_lai_lo(ma_nguoi_dung):
    """
    Tính toán trạng thái tài sản hiện tại của người dùng.

    Trả về:
        ket_qua     : list các dict, mỗi dict là 1 mã CP đang giữ
        tong_von    : Tổng giá trị vốn đã bỏ ra (tính theo giá vốn TB)
        tong_hien_tai: Tổng giá trị hiện tại (tính theo giá thị trường)
        thong_tin_nguoi_dung: dict chứa TienMat, TongLaiLoChot
    """
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()

    # Lấy danh mục đang nắm giữ (SoLuongHienTai > 0)
    cursor.execute(
        "SELECT MaCoPhieu, SoLuongHienTai, GiaVon FROM DANHMUC WHERE MaNguoiDung = ? AND SoLuongHienTai > 0",
        (ma_nguoi_dung,)
    )
    danh_sach_cp = cursor.fetchall()

    # Lấy thông tin tài chính của người dùng (tiền mặt, lãi/lỗ đã chốt)
    cursor.execute(
        "SELECT TienMat, TongLaiLoChot, VonGoc FROM NGUOIDUNG WHERE MaNguoiDung = ?",
        (ma_nguoi_dung,)
    )
    hang_nguoi_dung = cursor.fetchone()
    conn.close()

    # Xử lý trường hợp người dùng chưa có thông tin tài chính
    if hang_nguoi_dung:
        tien_mat, tong_lai_lo_chot, von_goc = hang_nguoi_dung
    else:
        tien_mat, tong_lai_lo_chot, von_goc = 0.0, 0.0, 0.0

    thong_tin_nguoi_dung = {
        'tien_mat': tien_mat or 0.0,
        'tong_lai_lo_chot': tong_lai_lo_chot or 0.0,
        'von_goc': von_goc or 0.0
    }

    ket_qua = []
    tong_von = 0.0
    tong_gia_tri_hien_tai = 0.0

    for hang in danh_sach_cp:
        ma_cp, so_luong, gia_von = hang

        # Lấy giá thị trường thực tế từ API
        gia_thi_truong = lay_gia_hien_tai(ma_cp)

        # Nếu lỗi không lấy được giá → tạm dùng giá vốn để không bị lỗi
        if gia_thi_truong == 0.0:
            gia_thi_truong = gia_von

        # Tính giá trị và lãi/lỗ chưa chốt (Unrealized P&L)
        gia_tri_von = so_luong * gia_von
        gia_tri_hien_tai = so_luong * gia_thi_truong

        # Unrealized P&L = Giá trị hiện tại - Giá trị vốn bỏ ra
        lai_lo_chua_chot = gia_tri_hien_tai - gia_tri_von

        # Tỷ lệ % lãi/lỗ
        phan_tram = (lai_lo_chua_chot / gia_tri_von * 100) if gia_tri_von > 0 else 0

        tong_von += gia_tri_von
        tong_gia_tri_hien_tai += gia_tri_hien_tai

        ket_qua.append({
            'ma_cp': ma_cp,
            'so_luong': so_luong,
            'gia_von': gia_von,
            'gia_hien_tai': gia_thi_truong,
            'gia_tri_von': gia_tri_von,
            'lai_lo': lai_lo_chua_chot,
            'phan_tram': phan_tram
        })

    return ket_qua, tong_von, tong_gia_tri_hien_tai, thong_tin_nguoi_dung


# ==============================================================
# HÀM LẤY LỊCH SỬ GIAO DỊCH (Sao kê dòng tiền)
# ==============================================================

def lay_lich_su_giao_dich(ma_nguoi_dung):
    """
    Lấy toàn bộ lịch sử giao dịch của người dùng, sắp xếp mới nhất lên đầu.
    Trả về list các dict chứa chi tiết từng giao dịch.
    """
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()

    cursor.execute(
        """SELECT MaGiaoDich, NgayGD, MaCoPhieu, LoaiGiaoDich, GiaKhop, KhoiLuong, ThanhTien, LaiLoChot
           FROM GIAODICH
           WHERE MaNguoiDung = ?
           ORDER BY MaGiaoDich DESC""",
        (ma_nguoi_dung,)
    )

    danh_sach = []
    for hang in cursor.fetchall():
        ma_gd, ngay, ma_cp, loai, gia, kl, thanh_tien, lai_lo_chot = hang
        danh_sach.append({
            'ma_gd': ma_gd,
            'ngay': ngay,
            'ma_cp': ma_cp,
            'loai': loai,
            'gia_khop': gia or 0.0,
            'khoi_luong': kl,
            # ThanhTien có thể NULL nếu dữ liệu cũ → tự tính lại
            'thanh_tien': thanh_tien if thanh_tien else (gia * kl),
            # LaiLoChot chỉ có giá trị với lệnh BÁN
            'lai_lo_chot': lai_lo_chot
        })

    conn.close()
    return danh_sach
