import random # <--- Nhớ import cái này ở đầu file

# --- KHO DỮ LIỆU MẪU (DATA SEED) ---
SAMPLE_ACTIVITIES = [
    {"title": "☕ Cafe Highland", "desc": "Ra ngồi ngắm phố phường và làm việc.", "icon": "☕", "color": "from-orange-400 to-red-500"},
    {"title": "🏃 Chạy bộ Hồ Tây", "desc": "Làm một vòng hồ cho khỏe người.", "icon": "🏃", "color": "from-cyan-400 to-blue-500"},
    {"title": "🎬 Xem phim rạp", "desc": "Check CGV xem bom tấn mới nhất.", "icon": "🎬", "color": "from-purple-400 to-pink-500"},
    {"title": "🍺 Nhậu Tạ Hiện", "desc": "Lên phố làm vài ly bia cỏ.", "icon": "🍺", "color": "from-yellow-400 to-orange-500"},
    {"title": "📚 Nhà sách Nhã Nam", "desc": "Đi mua vài cuốn sách về đọc.", "icon": "📚", "color": "from-green-400 to-emerald-500"},
    {"title": "🧹 Tổng vệ sinh", "desc": "Dọn dẹp phòng ốc sạch bong kin kít.", "icon": "🧹", "color": "from-gray-400 to-gray-600"},
    {"title": "🍜 Phở Bát Đàn", "desc": "Đi ăn bát phở nóng hổi.", "icon": "🍜", "color": "from-orange-300 to-yellow-500"},
    {"title": "📸 Chụp ảnh Film", "desc": "Xách máy film đi chụp phố cổ.", "icon": "📸", "color": "from-indigo-400 to-purple-600"},
    {"title": "🎮 Chơi Game PC", "desc": "Làm vài ván League of Legends hoặc CS2.", "icon": "🎮", "color": "from-red-500 to-pink-600"},
    {"title": "🧘 Thiền 15p", "desc": "Tịnh tâm, gạt bỏ lo âu.", "icon": "🧘", "color": "from-teal-400 to-green-400"},
    {"title": "🐶 Dắt chó đi dạo", "desc": "Cho boss đi hóng gió.", "icon": "🐶", "color": "from-yellow-600 to-yellow-800"},
    {"title": "💻 Code dạo", "desc": "Học thêm một framework mới.", "icon": "💻", "color": "from-slate-700 to-slate-900"},
    {"title": "🛒 Đi siêu thị", "desc": "Mua đồ ăn tích trữ cho tuần tới.", "icon": "🛒", "color": "from-blue-400 to-indigo-500"},
    {"title": "🎨 Vẽ tranh", "desc": "Mua màu về vẽ vời linh tinh.", "icon": "🎨", "color": "from-pink-300 to-rose-400"},
    {"title": "🎤 Karaoke", "desc": "Hát hò xả stress với bạn bè.", "icon": "🎤", "color": "from-violet-500 to-fuchsia-600"},
    {"title": "🏕️ Cắm trại Ecopark", "desc": "Cuối tuần đi picnic đổi gió.", "icon": "🏕️", "color": "from-green-600 to-lime-500"},
    {"title": "🎱 Bida lỗ", "desc": "Làm vài cơ bi-a với anh em.", "icon": "🎱", "color": "from-gray-800 to-black"},
    {"title": "🏸 Đánh cầu lông", "desc": "Vận động nhẹ nhàng buổi chiều.", "icon": "🏸", "color": "from-blue-300 to-cyan-400"},
    {"title": "🥩 Nướng BBQ", "desc": "Tự mua thịt về nướng tại gia.", "icon": "🥩", "color": "from-red-600 to-orange-700"},
    {"title": "💆 Gội đầu dưỡng sinh", "desc": "Thư giãn đầu óc, massage cổ vai gáy.", "icon": "💆", "color": "from-teal-200 to-teal-400"}
]

# --- API MỚI: LẤY GỢI Ý (SUGGESTIONS) ---
@app.get("/api/suggestions")
def get_suggestions():
    # Mỗi lần gọi sẽ trả về 10 hoạt động ngẫu nhiên từ kho
    # Xáo trộn danh sách
    shuffled = random.sample(SAMPLE_ACTIVITIES, len(SAMPLE_ACTIVITIES))
    # Gán ID giả để React không bị lỗi key
    results = []
    for idx, item in enumerate(shuffled[:10]): # Lấy 10 cái đầu
        results.append({
            "id": idx + 1000, # ID to để không trùng ID trong DB
            "title": item["title"],
            "desc": item["desc"],
            "icon": item["icon"],
            "color": item["color"]
        })
    return results