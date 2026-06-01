"""
database.py - Khởi tạo và quản lý cơ sở dữ liệu SQLite
Dự án: Hệ thống Quản lý và Phân tích Danh mục Đầu tư Chứng khoán Cá nhân
Sinh viên: Trần Minh Khánh - NEU
"""

import sqlite3


def ket_noi_db():
    """Tạo và trả về kết nối đến file database portfolio.db"""
    return sqlite3.connect('portfolio.db')


def init_db():
    """
    Khởi tạo toàn bộ cấu trúc database.
    Gọi hàm này 1 lần khi khởi động ứng dụng.
    Nếu bảng đã tồn tại thì bỏ qua (IF NOT EXISTS).
    """
    conn = ket_noi_db()
    cursor = conn.cursor()

    # =========================================================
    # BẢNG 1: NGUOIDUNG
    # Lưu thông tin tài khoản người dùng
    # =========================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS NGUOIDUNG (
            MaNguoiDung  INTEGER PRIMARY KEY AUTOINCREMENT,
            TenDangNhap  TEXT UNIQUE NOT NULL,
            MatKhau      TEXT NOT NULL,
            HoTen        TEXT,
            -- VonGoc: Tổng số tiền gốc người dùng nạp vào để đầu tư (đồng VNĐ)
            VonGoc       REAL DEFAULT 0.0,
            -- TienMat: Số tiền mặt còn lại sau khi mua/bán (chưa tính vào cổ phiếu đang giữ)
            TienMat      REAL DEFAULT 0.0,
            -- TongLaiLoChot: Tổng lãi/lỗ ĐÃ CHỐT (Realized P&L) tích lũy từ tất cả lệnh bán
            TongLaiLoChot REAL DEFAULT 0.0
        )
    ''')

    # =========================================================
    # BẢNG 2: DANHMUC
    # Lưu trạng thái danh mục ĐANG NẮM GIỮ (hiện tại)
    # Mỗi mã cổ phiếu là một dòng, cập nhật liên tục khi mua/bán
    # =========================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS DANHMUC (
            MaDanhMuc      INTEGER PRIMARY KEY AUTOINCREMENT,
            MaNguoiDung    INTEGER NOT NULL,
            MaCoPhieu      TEXT NOT NULL,
            -- SoLuongHienTai: Số lượng cổ phiếu đang nắm giữ
            SoLuongHienTai INTEGER DEFAULT 0,
            -- GiaVon: Giá vốn trung bình (Tổng tiền đã mua / Tổng số lượng mua)
            -- QUAN TRỌNG: GiaVon KHÔNG thay đổi khi BÁN, chỉ thay đổi khi MUA thêm
            GiaVon         REAL DEFAULT 0.0,
            FOREIGN KEY (MaNguoiDung) REFERENCES NGUOIDUNG(MaNguoiDung)
        )
    ''')

    # =========================================================
    # BẢNG 3: GIAODICH
    # Lưu lịch sử toàn bộ lệnh Mua/Bán (sao kê dòng tiền)
    # Không bao giờ xóa dữ liệu ở bảng này
    # =========================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GIAODICH (
            MaGiaoDich    INTEGER PRIMARY KEY AUTOINCREMENT,
            MaNguoiDung   INTEGER NOT NULL,
            MaCoPhieu     TEXT NOT NULL,
            LoaiGiaoDich  TEXT CHECK(LoaiGiaoDich IN ('MUA', 'BAN')) NOT NULL,
            GiaKhop       REAL NOT NULL,
            KhoiLuong     INTEGER NOT NULL,
            -- ThanhTien: Tổng giá trị giao dịch = GiaKhop * KhoiLuong
            ThanhTien     REAL NOT NULL,
            -- LaiLoChot: Chỉ có giá trị khi LoaiGiaoDich = 'BAN'
            --            = (GiaBan - GiaVonTB) * KhoiLuong
            --            Dương = Lãi, Âm = Lỗ, NULL nếu là lệnh MUA
            LaiLoChot     REAL DEFAULT NULL,
            NgayGD        TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (MaNguoiDung) REFERENCES NGUOIDUNG(MaNguoiDung)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Khởi tạo Database thành công!")


def nang_cap_db():
    """
    Nâng cấp database cũ (nếu người dùng đã có portfolio.db từ phiên bản trước).
    Thêm các cột mới nếu chưa tồn tại, tránh lỗi khi chạy lại app.
    """
    conn = ket_noi_db()
    cursor = conn.cursor()

    # Lấy danh sách cột hiện có của bảng NGUOIDUNG
    cursor.execute("PRAGMA table_info(NGUOIDUNG)")
    cot_nguoi_dung = [row[1] for row in cursor.fetchall()]

    # Thêm cột VonGoc nếu chưa có (database cũ không có cột này)
    if 'VonGoc' not in cot_nguoi_dung:
        cursor.execute("ALTER TABLE NGUOIDUNG ADD COLUMN VonGoc REAL DEFAULT 0.0")
        print("  → Đã thêm cột VonGoc vào bảng NGUOIDUNG")

    # Thêm cột TienMat nếu chưa có
    if 'TienMat' not in cot_nguoi_dung:
        cursor.execute("ALTER TABLE NGUOIDUNG ADD COLUMN TienMat REAL DEFAULT 0.0")
        print("  → Đã thêm cột TienMat vào bảng NGUOIDUNG")

    # Thêm cột TongLaiLoChot nếu chưa có
    if 'TongLaiLoChot' not in cot_nguoi_dung:
        cursor.execute("ALTER TABLE NGUOIDUNG ADD COLUMN TongLaiLoChot REAL DEFAULT 0.0")
        print("  → Đã thêm cột TongLaiLoChot vào bảng NGUOIDUNG")

    # Lấy danh sách cột hiện có của bảng GIAODICH
    cursor.execute("PRAGMA table_info(GIAODICH)")
    cot_giao_dich = [row[1] for row in cursor.fetchall()]

    # Thêm cột ThanhTien nếu chưa có
    if 'ThanhTien' not in cot_giao_dich:
        cursor.execute("ALTER TABLE GIAODICH ADD COLUMN ThanhTien REAL DEFAULT 0.0")
        print("  → Đã thêm cột ThanhTien vào bảng GIAODICH")

    # Thêm cột LaiLoChot nếu chưa có
    if 'LaiLoChot' not in cot_giao_dich:
        cursor.execute("ALTER TABLE GIAODICH ADD COLUMN LaiLoChot REAL DEFAULT NULL")
        print("  → Đã thêm cột LaiLoChot vào bảng GIAODICH")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    nang_cap_db()
