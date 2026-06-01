"""
main_ui.py - Giao diện người dùng chính (Tkinter + ttk)
Dự án: Hệ thống Quản lý và Phân tích Danh mục Đầu tư Chứng khoán Cá nhân
Sinh viên: Trần Minh Khánh - NEU

Cấu trúc giao diện:
  - Tab 1 "Bảng Điều Khiển": Form nhập lệnh + Bảng danh mục + Biểu đồ Pie Chart + Chỉ số tổng quan
  - Tab 2 "Lịch Sử Giao Dịch": Sao kê toàn bộ lệnh mua/bán với Realized P&L
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# Matplotlib để vẽ biểu đồ nhúng vào Tkinter
import matplotlib
matplotlib.use('TkAgg')  # Phải gọi trước khi import pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import database
import logic

# ============================================================
# HẰNG SỐ TOÀN CỤC
# ============================================================
MA_NGUOI_DUNG = 1   # ID người dùng mặc định (Trần Minh Khánh)

# Màu sắc cho giao diện
MAU_XANH_DAM  = "#1a73e8"
MAU_XANH_NHAT = "#e8f0fe"
MAU_XANH_LA   = "#0f9d58"
MAU_DO        = "#d93025"
MAU_CAM       = "#f57c00"
MAU_XAM_NEN   = "#f5f5f5"
MAU_TRANG     = "#ffffff"
MAU_CHU_TIEU  = "#5f6368"

# ============================================================
# PHẦN 1: KHỞI TẠO DỮ LIỆU
# ============================================================

def tao_user_mac_dinh():
    """Tạo người dùng mặc định nếu chưa tồn tại (dùng để chạy thử)."""
    conn = database.ket_noi_db()
    cursor = conn.cursor()
    cursor.execute("SELECT MaNguoiDung FROM NGUOIDUNG WHERE MaNguoiDung = 1")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO NGUOIDUNG (TenDangNhap, MatKhau, HoTen, VonGoc, TienMat, TongLaiLoChot) "
            "VALUES ('khanhtm', '123456', 'Trần Minh Khánh', 0.0, 0.0, 0.0)"
        )
        conn.commit()
        print("✅ Đã tạo người dùng mặc định: Trần Minh Khánh")
    conn.close()


# ============================================================
# PHẦN 2: XỬ LÝ LỆNH GIAO DỊCH
# ============================================================

def them_giao_dich():
    """
    Xử lý sự kiện khi nhấn nút "Thêm Giao Dịch".
    Đọc dữ liệu từ form, validate, gọi logic tương ứng (mua/bán),
    sau đó làm mới toàn bộ giao diện.
    """
    ma_cp = entry_ma_cp.get().strip().upper()
    loai_gd = combo_loai_gd.get()

    # --- Validate đầu vào ---
    if not ma_cp:
        messagebox.showerror("Lỗi nhập liệu", "Vui lòng nhập Mã cổ phiếu!\nVD: SHB, VNM, HPG")
        return

    try:
        gia_khop = float(entry_gia.get().replace(',', ''))  # Cho phép nhập giá có dấu phẩy
        khoi_luong = int(entry_khoi_luong.get().replace(',', ''))
        if gia_khop <= 0 or khoi_luong <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Lỗi nhập liệu", "Giá khớp và Khối lượng phải là số dương!\n"
                                               "VD: Giá = 14750, Khối lượng = 100")
        return

    # --- Kết nối DB và thực hiện giao dịch ---
    conn = database.ket_noi_db()
    cursor = conn.cursor()

    try:
        if loai_gd == "MUA":
            logic.xu_ly_mua_co_phieu(cursor, MA_NGUOI_DUNG, ma_cp, gia_khop, khoi_luong)
            conn.commit()
            thanh_tien = gia_khop * khoi_luong
            messagebox.showinfo(
                "✅ Mua thành công",
                f"Đã mua {khoi_luong:,} cổ phiếu {ma_cp}\n"
                f"Giá khớp: {gia_khop:,.0f} VNĐ\n"
                f"Thành tiền: {thanh_tien:,.0f} VNĐ"
            )

        elif loai_gd == "BAN":
            thanh_cong, ket_qua = logic.xu_ly_ban_co_phieu(cursor, MA_NGUOI_DUNG, ma_cp, gia_khop, khoi_luong)
            if not thanh_cong:
                # ket_qua lúc này là thông báo lỗi
                messagebox.showerror("❌ Lỗi giao dịch", ket_qua)
                conn.close()
                return
            conn.commit()
            lai_lo_chot = ket_qua  # ket_qua lúc này là số tiền lãi/lỗ
            thanh_tien_ban = gia_khop * khoi_luong

            # Hiển thị kết quả lãi/lỗ đã chốt sau khi bán
            if lai_lo_chot >= 0:
                ket_qua_text = f"🟢 Lãi đã chốt: +{lai_lo_chot:,.0f} VNĐ"
            else:
                ket_qua_text = f"🔴 Lỗ đã chốt: {lai_lo_chot:,.0f} VNĐ"

            messagebox.showinfo(
                "✅ Bán thành công",
                f"Đã bán {khoi_luong:,} cổ phiếu {ma_cp}\n"
                f"Giá bán: {gia_khop:,.0f} VNĐ\n"
                f"Thu về: {thanh_tien_ban:,.0f} VNĐ\n"
                f"──────────────────\n"
                f"{ket_qua_text}"
            )

    except Exception as loi:
        conn.rollback()  # Hoàn tác nếu có lỗi
        messagebox.showerror("Lỗi hệ thống", f"Có lỗi xảy ra:\n{loi}")
    finally:
        conn.close()

    # Xóa form sau khi thêm xong
    entry_ma_cp.delete(0, tk.END)
    entry_gia.delete(0, tk.END)
    entry_khoi_luong.delete(0, tk.END)

    # Làm mới toàn bộ dữ liệu hiển thị
    tai_lai_toan_bo()


# ============================================================
# PHẦN 3: HIỂN THỊ DỮ LIỆU DANH MỤC
# ============================================================

def tai_lai_toan_bo():
    """
    Điều phối làm mới toàn bộ giao diện:
    1. Cập nhật bảng danh mục (Unrealized P&L)
    2. Cập nhật các chỉ số tổng quan
    3. Vẽ lại biểu đồ phân bổ vốn
    4. Cập nhật bảng lịch sử giao dịch
    """
    cap_nhat_bang_danh_muc()
    cap_nhat_bieu_do()
    cap_nhat_lich_su_giao_dich()


def cap_nhat_bang_danh_muc():
    """
    Xóa và tải lại bảng danh mục + cập nhật các ô chỉ số tổng quan.
    Màu sắc: dòng Lãi → xanh lá, dòng Lỗ → đỏ.
    """
    # Xóa dữ liệu cũ trên bảng
    for hang in tree_danh_muc.get_children():
        tree_danh_muc.delete(hang)

    # Gọi logic để tính toán
    ket_qua, tong_von, tong_hien_tai, thong_tin_nd = logic.tinh_toan_lai_lo(MA_NGUOI_DUNG)

    # Đổ dữ liệu lên bảng
    for item in ket_qua:
        # Định dạng % lãi/lỗ với dấu + hoặc -
        phan_tram_str = f"+{item['phan_tram']:.2f}%" if item['phan_tram'] >= 0 else f"{item['phan_tram']:.2f}%"
        lai_lo_str = f"+{item['lai_lo']:,.0f}" if item['lai_lo'] >= 0 else f"{item['lai_lo']:,.0f}"

        hang_id = tree_danh_muc.insert("", tk.END, values=(
            item['ma_cp'],
            f"{item['so_luong']:,}",
            f"{item['gia_von']:,.0f}",
            f"{item['gia_hien_tai']:,.0f}",
            f"{item['gia_tri_von']:,.0f}",
            lai_lo_str,
            phan_tram_str
        ))

        # Tô màu dòng theo kết quả lãi/lỗ
        if item['lai_lo'] >= 0:
            tree_danh_muc.tag_configure('lai', foreground='#0f9d58')
            tree_danh_muc.item(hang_id, tags=('lai',))
        else:
            tree_danh_muc.tag_configure('lo', foreground='#d93025')
            tree_danh_muc.item(hang_id, tags=('lo',))

    # Tính các chỉ số tổng quan
    tong_lai_lo_chua_chot = tong_hien_tai - tong_von
    tong_tai_san = tong_hien_tai + thong_tin_nd['tien_mat']
    tong_lai_lo_chot = thong_tin_nd['tong_lai_lo_chot']

    # Cập nhật các ô hiển thị chỉ số
    def dinh_dang_so_mau(so):
        """Trả về chuỗi định dạng có dấu + và màu tương ứng."""
        if so >= 0:
            return f"+{so:,.0f} VNĐ", MAU_XANH_LA
        else:
            return f"{so:,.0f} VNĐ", MAU_DO

    lbl_tong_tai_san.config(text=f"{tong_tai_san:,.0f} VNĐ")
    lbl_tong_von.config(text=f"{tong_von:,.0f} VNĐ")
    lbl_tien_mat.config(text=f"{thong_tin_nd['tien_mat']:,.0f} VNĐ")

    text_chua_chot, mau_chua_chot = dinh_dang_so_mau(tong_lai_lo_chua_chot)
    lbl_lai_lo_chua_chot.config(text=text_chua_chot, foreground=mau_chua_chot)

    text_da_chot, mau_da_chot = dinh_dang_so_mau(tong_lai_lo_chot)
    lbl_lai_lo_da_chot.config(text=text_da_chot, foreground=mau_da_chot)


# ============================================================
# PHẦN 4: BIỂU ĐỒ PIE CHART (Matplotlib nhúng vào Tkinter)
# ============================================================

def cap_nhat_bieu_do():
    """
    Vẽ biểu đồ hình tròn (Pie Chart) thể hiện tỷ trọng phân bổ vốn
    theo từng mã cổ phiếu trong danh mục hiện tại.
    Biểu đồ được nhúng trực tiếp vào Tab 1, tự động cập nhật khi dữ liệu thay đổi.
    """
    # Xóa biểu đồ cũ để vẽ lại
    ax_pie.clear()

    # Lấy dữ liệu danh mục (không cần gọi API lại, dùng GiaVon × SoLuong)
    conn = database.ket_noi_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT MaCoPhieu, SoLuongHienTai * GiaVon FROM DANHMUC WHERE MaNguoiDung = ? AND SoLuongHienTai > 0",
        (MA_NGUOI_DUNG,)
    )
    du_lieu = cursor.fetchall()
    conn.close()

    if not du_lieu:
        # Khi danh mục trống: hiển thị thông báo thay vì biểu đồ rỗng
        ax_pie.text(
            0.5, 0.5, "Danh mục trống\nHãy thêm giao dịch MUA",
            ha='center', va='center', fontsize=10,
            color=MAU_CHU_TIEU, transform=ax_pie.transAxes
        )
        ax_pie.set_title("Phân bổ danh mục theo vốn đầu tư", fontsize=11, fontweight='bold', pad=10)
        canvas_bieu_do.draw()
        return

    # Tách nhãn (mã CP) và giá trị (số tiền đã đầu tư)
    nhan = [hang[0] for hang in du_lieu]
    gia_tri = [hang[1] for hang in du_lieu]

    # Màu sắc cho các lát pie (bảng màu hài hòa)
    bang_mau = [
        '#4285F4', '#0F9D58', '#F4B400', '#DB4437', '#AB47BC',
        '#00ACC1', '#FF7043', '#9E9D24', '#5C6BC0', '#26A69A'
    ]

    # Highlight lát lớn nhất (explode nhẹ)
    vi_tri_lon_nhat = gia_tri.index(max(gia_tri))
    do_tach = [0.05 if i == vi_tri_lon_nhat else 0 for i in range(len(gia_tri))]

    # Vẽ biểu đồ
    goc_dau, phan_tram_tu_dong, nhan_hien_thi = ax_pie.pie(
        gia_tri,
        labels=nhan,
        colors=bang_mau[:len(nhan)],
        autopct='%1.1f%%',       # Hiển thị % tự động
        startangle=90,           # Bắt đầu từ 12 giờ
        explode=do_tach,
        pctdistance=0.75,        # Vị trí hiển thị % (trong lát)
        wedgeprops=dict(linewidth=1.5, edgecolor='white')  # Đường viền trắng giữa các lát
    )

    # Định dạng font chữ % và nhãn
    for text in phan_tram_tu_dong:
        text.set_fontsize(8)
        text.set_fontweight('bold')
    for text in nhan_hien_thi:
        text.set_fontsize(9)
        text.set_fontweight('bold')

    ax_pie.set_title("Phân bổ vốn đầu tư theo mã cổ phiếu", fontsize=11, fontweight='bold', pad=12)

    # Cập nhật canvas (vẽ lại)
    canvas_bieu_do.draw()


# ============================================================
# PHẦN 5: LỊCH SỬ GIAO DỊCH (Tab 2)
# ============================================================

def cap_nhat_lich_su_giao_dich():
    """Xóa và tải lại toàn bộ lịch sử giao dịch lên Tab 2."""
    for hang in tree_lich_su.get_children():
        tree_lich_su.delete(hang)

    danh_sach = logic.lay_lich_su_giao_dich(MA_NGUOI_DUNG)

    for gd in danh_sach:
        # Định dạng dòng tiền: MUA = "-" (tiêu tiền), BÁN = "+" (thu tiền)
        if gd['loai'] == 'MUA':
            dong_tien_str = f"- {gd['thanh_tien']:,.0f}"
        else:
            dong_tien_str = f"+ {gd['thanh_tien']:,.0f}"

        # Lãi/lỗ chốt chỉ hiển thị với lệnh BÁN
        if gd['loai'] == 'BAN' and gd['lai_lo_chot'] is not None:
            ll = gd['lai_lo_chot']
            lai_lo_str = f"+{ll:,.0f}" if ll >= 0 else f"{ll:,.0f}"
        else:
            lai_lo_str = "—"  # Lệnh MUA không có Realized P&L

        hang_id = tree_lich_su.insert("", tk.END, values=(
            gd['ngay'][:16] if gd['ngay'] else "",  # Cắt bỏ giây, chỉ giữ YYYY-MM-DD HH:MM
            gd['ma_cp'],
            gd['loai'],
            f"{gd['gia_khop']:,.0f}",
            f"{gd['khoi_luong']:,}",
            dong_tien_str,
            lai_lo_str
        ))

        # Tô màu: hàng BÁN lãi → xanh, BÁN lỗ → đỏ, MUA → mặc định
        if gd['loai'] == 'BAN':
            if gd['lai_lo_chot'] and gd['lai_lo_chot'] >= 0:
                tree_lich_su.item(hang_id, tags=('ban_lai',))
            else:
                tree_lich_su.item(hang_id, tags=('ban_lo',))


# ============================================================
# PHẦN 6: XÂY DỰNG GIAO DIỆN CHÍNH
# ============================================================

# --- Khởi tạo database và người dùng ---
database.init_db()
database.nang_cap_db()
tao_user_mac_dinh()

# --- Cửa sổ chính ---
root = tk.Tk()
root.title("📈 Quản lý Danh mục Đầu tư Chứng khoán")
root.geometry("1200x750")
root.configure(bg=MAU_XAM_NEN)
root.minsize(900, 600)

# --- Style cho ttk ---
style = ttk.Style()
style.theme_use('clam')  # Theme 'clam' trông hiện đại hơn 'default' trên Windows

# Tùy chỉnh style cho Notebook (Tab bar)
style.configure('TNotebook', background=MAU_XAM_NEN, borderwidth=0)
style.configure('TNotebook.Tab', font=('Arial', 10, 'bold'), padding=[16, 8])
style.map('TNotebook.Tab', background=[('selected', MAU_XANH_DAM), ('!selected', '#e0e0e0')],
          foreground=[('selected', 'white'), ('!selected', '#333333')])

# Tùy chỉnh Treeview
style.configure('Treeview', font=('Arial', 9), rowheight=26)
style.configure('Treeview.Heading', font=('Arial', 9, 'bold'), background=MAU_XANH_DAM, foreground='white')
style.map('Treeview', background=[('selected', MAU_XANH_NHAT)])

# ============================================================
# TẠO NOTEBOOK (SYSTEM TAB)
# ============================================================
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True, padx=10, pady=10)

# =====================================================
# TAB 1: BẢNG ĐIỀU KHIỂN (DASHBOARD)
# =====================================================
tab_dashboard = ttk.Frame(notebook, style='TFrame')
notebook.add(tab_dashboard, text='  📊 Bảng Điều Khiển  ')

# ------ Cột trái (Form + Bảng danh mục) ------
frame_trai = tk.Frame(tab_dashboard, bg=MAU_XAM_NEN)
frame_trai.pack(side='left', fill='both', expand=True, padx=(5, 3), pady=5)

# --- Khu vực FORM NHẬP LỆNH ---
frame_form = tk.LabelFrame(
    frame_trai, text="  📝 Nhập Lệnh Giao Dịch  ",
    font=('Arial', 10, 'bold'), bg=MAU_TRANG, fg=MAU_XANH_DAM,
    relief='groove', bd=2, padx=12, pady=10
)
frame_form.pack(fill='x', pady=(0, 6))

# Hàng 1: Mã CP + Loại GD
tk.Label(frame_form, text="Mã CP:", font=('Arial', 9, 'bold'), bg=MAU_TRANG).grid(row=0, column=0, sticky='e', padx=5, pady=4)
entry_ma_cp = tk.Entry(frame_form, width=8, font=('Arial', 10, 'bold'))
entry_ma_cp.grid(row=0, column=1, padx=5, pady=4)

tk.Label(frame_form, text="Loại:", font=('Arial', 9, 'bold'), bg=MAU_TRANG).grid(row=0, column=2, sticky='e', padx=5)
combo_loai_gd = ttk.Combobox(frame_form, values=["MUA", "BAN"], width=6, font=('Arial', 10, 'bold'), state='readonly')
combo_loai_gd.current(0)
combo_loai_gd.grid(row=0, column=3, padx=5, pady=4)

tk.Label(frame_form, text="Giá khớp (VNĐ):", font=('Arial', 9, 'bold'), bg=MAU_TRANG).grid(row=0, column=4, sticky='e', padx=5)
entry_gia = tk.Entry(frame_form, width=12, font=('Arial', 10))
entry_gia.grid(row=0, column=5, padx=5, pady=4)

tk.Label(frame_form, text="Khối lượng:", font=('Arial', 9, 'bold'), bg=MAU_TRANG).grid(row=0, column=6, sticky='e', padx=5)
entry_khoi_luong = tk.Entry(frame_form, width=10, font=('Arial', 10))
entry_khoi_luong.grid(row=0, column=7, padx=5, pady=4)

# Nút "Thêm Giao Dịch" với màu xanh lá nổi bật
btn_them = tk.Button(
    frame_form, text="✔ Xác nhận", font=('Arial', 10, 'bold'),
    bg=MAU_XANH_LA, fg='white', relief='flat', cursor='hand2',
    padx=12, pady=4, command=them_giao_dich
)
btn_them.grid(row=0, column=8, padx=10, pady=4)

# Nút "Làm mới" để cập nhật giá live
btn_lam_moi = tk.Button(
    frame_form, text="🔄 Làm mới giá", font=('Arial', 9),
    bg=MAU_XANH_DAM, fg='white', relief='flat', cursor='hand2',
    padx=8, pady=4, command=tai_lai_toan_bo
)
btn_lam_moi.grid(row=0, column=9, padx=5, pady=4)

# --- Khu vực BẢNG DANH MỤC ĐANG GIỮ ---
frame_bang = tk.LabelFrame(
    frame_trai, text="  📋 Danh Mục Đang Nắm Giữ  ",
    font=('Arial', 10, 'bold'), bg=MAU_TRANG, fg=MAU_XANH_DAM,
    relief='groove', bd=2
)
frame_bang.pack(fill='both', expand=True)

cot_danh_muc = ("Mã CP", "Số Lượng", "Giá Vốn TB", "Giá Hiện Tại", "Giá Trị Vốn", "Lãi/Lỗ Chưa Chốt", "%")
tree_danh_muc = ttk.Treeview(frame_bang, columns=cot_danh_muc, show='headings', height=10)

do_rong_cot = [70, 80, 110, 120, 130, 150, 70]
for i, (cot, rong) in enumerate(zip(cot_danh_muc, do_rong_cot)):
    tree_danh_muc.heading(cot, text=cot)
    tree_danh_muc.column(cot, width=rong, anchor='center')

# Thanh cuộn dọc cho bảng danh mục
scrollbar_danh_muc = ttk.Scrollbar(frame_bang, orient='vertical', command=tree_danh_muc.yview)
tree_danh_muc.configure(yscrollcommand=scrollbar_danh_muc.set)
tree_danh_muc.pack(side='left', fill='both', expand=True, padx=5, pady=5)
scrollbar_danh_muc.pack(side='right', fill='y', pady=5)

# ------ Cột phải (Chỉ số tổng quan + Biểu đồ) ------
frame_phai = tk.Frame(tab_dashboard, bg=MAU_XAM_NEN, width=310)
frame_phai.pack(side='right', fill='y', padx=(3, 5), pady=5)
frame_phai.pack_propagate(False)  # Giữ nguyên chiều rộng cố định

# --- Khu vực CÁC CHỈ SỐ TỔNG QUAN ---
frame_chi_so = tk.LabelFrame(
    frame_phai, text="  💰 Chỉ Số Tổng Quan  ",
    font=('Arial', 10, 'bold'), bg=MAU_TRANG, fg=MAU_XANH_DAM,
    relief='groove', bd=2, padx=10, pady=8
)
frame_chi_so.pack(fill='x', pady=(0, 6))

def tao_hang_chi_so(parent, ten, hang, mau_ten="#5f6368"):
    """Tạo một hàng hiển thị chỉ số gồm nhãn tên và nhãn giá trị."""
    tk.Label(parent, text=ten, font=('Arial', 9), bg=MAU_TRANG, fg=mau_ten).grid(
        row=hang, column=0, sticky='w', pady=3
    )
    lbl_gia_tri = tk.Label(parent, text="—", font=('Arial', 10, 'bold'), bg=MAU_TRANG, fg='#202124')
    lbl_gia_tri.grid(row=hang, column=1, sticky='e', padx=(10, 0), pady=3)
    return lbl_gia_tri

frame_chi_so.columnconfigure(1, weight=1)

lbl_tong_tai_san   = tao_hang_chi_so(frame_chi_so, "📦 Tổng tài sản:",      0)
lbl_tong_von       = tao_hang_chi_so(frame_chi_so, "💼 Vốn đang đầu tư:",  1)
lbl_tien_mat       = tao_hang_chi_so(frame_chi_so, "💵 Tiền mặt:",          2)

# Đường kẻ phân cách
ttk.Separator(frame_chi_so, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)

lbl_lai_lo_chua_chot = tao_hang_chi_so(frame_chi_so, "📈 L/L chưa chốt:",   4)
lbl_lai_lo_da_chot   = tao_hang_chi_so(frame_chi_so, "✅ L/L đã chốt:",      5)

# --- Khu vực BIỂU ĐỒ PIE CHART ---
frame_bieu_do = tk.LabelFrame(
    frame_phai, text="  🥧 Phân Bổ Danh Mục  ",
    font=('Arial', 10, 'bold'), bg=MAU_TRANG, fg=MAU_XANH_DAM,
    relief='groove', bd=2
)
frame_bieu_do.pack(fill='both', expand=True)

# Tạo Figure của Matplotlib với nền trong suốt
fig_pie, ax_pie = plt.subplots(figsize=(3.2, 3.2))
fig_pie.patch.set_facecolor(MAU_TRANG)  # Nền trắng cho figure
ax_pie.set_facecolor(MAU_TRANG)

# Nhúng Figure vào Tkinter Frame thông qua FigureCanvasTkAgg
canvas_bieu_do = FigureCanvasTkAgg(fig_pie, master=frame_bieu_do)
canvas_bieu_do.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)

# =====================================================
# TAB 2: LỊCH SỬ GIAO DỊCH
# =====================================================
tab_lich_su = ttk.Frame(notebook, style='TFrame')
notebook.add(tab_lich_su, text='  📜 Lịch Sử Giao Dịch  ')

# Tiêu đề Tab 2
tk.Label(
    tab_lich_su,
    text="Sao kê toàn bộ lệnh Mua / Bán  |  Cột 'Lãi/Lỗ Đã Chốt' chỉ có giá trị với lệnh BÁN",
    font=('Arial', 9, 'italic'), fg=MAU_CHU_TIEU, bg=MAU_XAM_NEN
).pack(anchor='w', padx=10, pady=(8, 2))

# Bảng lịch sử giao dịch
frame_lich_su = tk.Frame(tab_lich_su, bg=MAU_XAM_NEN)
frame_lich_su.pack(fill='both', expand=True, padx=10, pady=5)

cot_lich_su = ("Ngày GD", "Mã CP", "Loại", "Giá Khớp", "Khối Lượng", "Dòng Tiền (VNĐ)", "Lãi/Lỗ Đã Chốt (VNĐ)")
tree_lich_su = ttk.Treeview(frame_lich_su, columns=cot_lich_su, show='headings', height=22)

do_rong_lich_su = [140, 80, 60, 110, 100, 160, 160]
for cot, rong in zip(cot_lich_su, do_rong_lich_su):
    tree_lich_su.heading(cot, text=cot)
    tree_lich_su.column(cot, width=rong, anchor='center')

# Màu sắc tag cho lịch sử
tree_lich_su.tag_configure('ban_lai', foreground='#0f9d58', font=('Arial', 9, 'bold'))
tree_lich_su.tag_configure('ban_lo',  foreground='#d93025', font=('Arial', 9, 'bold'))

# Thanh cuộn dọc
scrollbar_lich_su = ttk.Scrollbar(frame_lich_su, orient='vertical', command=tree_lich_su.yview)
tree_lich_su.configure(yscrollcommand=scrollbar_lich_su.set)
tree_lich_su.pack(side='left', fill='both', expand=True)
scrollbar_lich_su.pack(side='right', fill='y')

# Thanh cuộn ngang
scrollbar_ngang = ttk.Scrollbar(tab_lich_su, orient='horizontal', command=tree_lich_su.xview)
tree_lich_su.configure(xscrollcommand=scrollbar_ngang.set)
scrollbar_ngang.pack(fill='x', padx=10)

# ============================================================
# PHẦN 7: THANH TRẠNG THÁI (Status Bar)
# ============================================================
frame_status = tk.Frame(root, bg='#e0e0e0', height=24)
frame_status.pack(fill='x', side='bottom')

lbl_status = tk.Label(
    frame_status,
    text="✅ Sẵn sàng  |  Dữ liệu giá được lấy realtime từ vnstock API (VCI)",
    font=('Arial', 8), bg='#e0e0e0', fg='#5f6368', anchor='w'
)
lbl_status.pack(side='left', padx=8)

lbl_sinh_vien = tk.Label(
    frame_status,
    text="Trần Minh Khánh | NEU",
    font=('Arial', 8, 'bold'), bg='#e0e0e0', fg=MAU_XANH_DAM
)
lbl_sinh_vien.pack(side='right', padx=8)

# ============================================================
# PHẦN 8: KHỞI ĐỘNG ỨNG DỤNG
# ============================================================
# Tải dữ liệu ngay khi mở app
tai_lai_toan_bo()

# Chạy vòng lặp chính của Tkinter
root.mainloop()
