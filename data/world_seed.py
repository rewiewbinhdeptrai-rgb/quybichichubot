"""
Seed dữ liệu World — City + Location (mục 31-32 trong spec).

Thay thế `characters.location` dạng String tự do bằng entity thật:
Character đứng ở đúng 1 Location, Location thuộc đúng 1 City. Di chuyển
trong cùng City miễn phí; sang City khác tốn `travel_cost` (Bảng) của City
đích — không có "đi lại tức thời miễn phí toàn bản đồ" (đúng tinh thần
mục 38: mọi thay đổi tài nguyên phải là transaction thật).

CITIES: (city_id, name_en, description_vi, economy, crime, mystical_activity,
         church_influence, travel_cost)
- economy/crime/mystical_activity: 0-100, dùng để hiển thị + có thể làm input
  cho World Event sau này (mục 47) — hiện tại là dữ liệu tĩnh thật, không giả.
- travel_cost: phí (Bảng) để DI CHUYỂN TỚI thành phố này từ một thành phố khác.
"""

CITIES = [
    ("backlund", "Backlund", "Thủ đô công nghiệp của Loen — trung tâm quyền lực, "
     "tiền bạc và cả những bí mật ẩn giấu sau ống khói nhà máy.", 70, 35, 40, "high", 0),
    ("tingen", "Tingen", "Thành phố tôn giáo — trung tâm quyền lực của Nhà thờ Đêm "
     "Vĩnh Hằng, nơi giáo hội và huyền bí giao thoa gần như công khai.", 55, 20, 55,
     "very_high", 250),
    ("trier", "Trier", "Hải cảng phồn hoa — nơi giao thương sầm uất và cũng là "
     "cửa ngõ cho hàng hóa (và bí mật) từ mọi vùng biển.", 65, 30, 30, "medium", 250),
    ("skruvi", "Skruvi", "Thị trấn học thuật nhỏ nổi tiếng với các nhà nghiên cứu "
     "huyền bí và những thư viện cấm.", 40, 15, 60, "low", 300),
    ("migas", "Migas", "Thủ đô sa mạc phía Nam — vùng đất của những bí thuật cổ "
     "xưa còn sót lại từ thời trước Cách mạng Công nghiệp.", 45, 40, 50, "medium", 350),
]

# (location_id, city_id, name_en, description_vi, location_type, mystical_activity)
LOCATIONS = [
    ("backlund_center", "backlund", "Trung tâm Backlund",
     "Quảng trường trung tâm, nơi bắt đầu của hầu hết mọi Character.", "square", 20),
    ("backlund_docks", "backlund", "Bến cảng Backlund",
     "Khu bến cảng ồn ào, nơi hàng hóa và tin đồn cùng cập bến.", "district", 25),
    ("backlund_church_district", "backlund", "Khu Nhà thờ Backlund",
     "Chi nhánh Nhà thờ Đêm Vĩnh Hằng tại Backlund.", "landmark", 45),
    ("backlund_slums", "backlund", "Khu ổ chuột Backlund",
     "Nơi tội phạm và những kẻ chạy trốn ẩn náu.", "district", 30),
    ("tingen_cathedral", "tingen", "Đại giáo đường Tingen",
     "Trung tâm quyền lực của Nhà thờ Đêm Vĩnh Hằng.", "landmark", 70),
    ("tingen_market", "tingen", "Chợ Tingen",
     "Khu chợ sầm uất dưới bóng giáo đường.", "district", 40),
    ("tingen_old_town", "tingen", "Phố cổ Tingen",
     "Khu phố cổ với những con hẻm ẩn chứa nhiều bí mật.", "district", 55),
    ("trier_harbor", "trier", "Bến cảng Trier",
     "Cảng biển lớn nhất Intis, tàu bè ra vào không ngớt.", "district", 20),
    ("trier_market", "trier", "Khu chợ Trier",
     "Chợ trung tâm buôn bán đủ loại hàng hóa từ khắp nơi.", "district", 25),
    ("trier_university", "trier", "Đại học Trier",
     "Học viện danh tiếng, nơi nhiều Beyonder ẩn mình làm học giả.", "landmark", 40),
    ("skruvi_library", "skruvi", "Thư viện cổ Skruvi",
     "Thư viện lưu trữ nhiều tài liệu huyền bí quý hiếm.", "landmark", 65),
    ("skruvi_observatory", "skruvi", "Đài quan sát Skruvi",
     "Nơi các nhà nghiên cứu quan sát thiên tượng và điềm báo.", "landmark", 60),
    ("migas_bazaar", "migas", "Chợ phiên Migas",
     "Khu chợ phiên sa mạc, nơi giao dịch cả những thứ cấm kỵ.", "district", 45),
    ("migas_ruins", "migas", "Phế tích cổ Migas",
     "Tàn tích của một nền văn minh cổ xưa, đầy rẫy nguy hiểm huyền bí.", "landmark", 75),
]

DEFAULT_LOCATION_ID = "backlund_center"
