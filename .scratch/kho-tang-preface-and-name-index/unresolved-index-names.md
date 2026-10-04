# Unresolved Story Name Index entries

806 Index Names (12 Xem aliases), 799 targets (198 story, 582 khao-di, 19 chu-thich); 14 unresolved. 26 resolved only by fuzzy match.

Fix each by hand in `story_name_index.json` (set the target's `textName`, and `footnote` for Chú thích targets).

| Printed name | Qualifier | Story | Location | Reason |
|---|---|---|---|---|
| Con ngỗng đất |  | 134 | khao-di | name not found in Story text | Con ngựa đất
| Cô gái con vua và ba công trạng |  | 164 | khao-di | name not found in Story text | Cô gái con vua và ba công trạng
| Jăng nghèo và Jăng nghèo |  | 200 | khao-di | name not found in Story text | Jăng nghèo và Jăng giàu
| Mục Liên thăm mẹ ở địa ngục |  | 19 | chu-thich | name not found in Story text | Truyện bà mẹ Mục Liên
| Nàng Út |  | 120 | khao-di | name not found in Story text | truly empty, delete this
| Nàng Út diễn ca |  | 126 | khao-di | name not found in Story text | truyện Nàng Út
| Năng Nhẫn Bất Năng Nhẫn hành |  | 7 | khao-di | name not found in Story text | Năng Nhẫn Bất Năng Nhẫn hành, story 06
| Người anh tham lam |  | 47 | khao-di | name not found in Story text | Người anh tham lam story 150 khao di
| Sọ Dừa, Kinh hóa |  | 128 | khao-di | name not found in Story text | truyện Sọ Dừa, story 163
| Tám cuộc phiêu lưu của tôn sư Pa-ra-mác-tha |  | 196 | chu-thich | name not found in Story text | footnote story 196 
| Thỏ rơ-pai |  | 60 | khao-di | name not found in Story text | story 87 khao di
| Thử thần và miêu thần |  |  |  | no Story number printed | it's referenced in story 02 and 03, but it's actually story 140
| Vè người hóa dế |  | 133 | khao-di | name not found in Story text | bài vè, it's actually in 133, but the search name should be người hoá dế, the highlight is bài vè
| Xử phiến đá |  | 120 | khao-di | name not found in Story text | Khao di story 110

## Manual fixes applied (2026-10-04)

All 14 unresolved entries were fixed by hand in `story_name_index.json`; every `textName` was checked against its Story text. Re-running `build_name_index.py` would undo these.

| Printed name | Fix |
|---|---|
| Con ngỗng đất | 134 Khảo dị; printed name corrected to "Con ngựa đất" (the misprint is dropped), textName "Con ngựa đất" |
| Cô gái con vua và ba công trạng | moved 164 → **163** Khảo dị (where the text is), textName as printed |
| Jăng nghèo và Jăng nghèo | 200, textName "Jăng nghèo và Jăng giàu" |
| Mục Liên thăm mẹ ở địa ngục | 19 Chú thích, Footnote 2, textName "Truyện bà mẹ Mục Liên" |
| Nàng Út | record deleted (not in Story 120) |
| Nàng Út diễn ca | 126, textName "truyện Nàng Út" |
| Năng Nhẫn Bất Năng Nhẫn hành | moved 7 → 6 (tập I), textName as printed |
| Người anh tham lam | wrong 47 target removed; the 150 target already existed |
| Sọ Dừa, Kinh hóa | kept on **128** (not 163: 163 never mentions Sọ Dừa), textName "truyện Sọ Dừa" |
| Tám cuộc phiêu lưu của tôn sư Pa-ra-mác-tha | 196 Chú thích, Footnote 3, textName "Tám cuộc phiêu lưu của tôn sư (gu-ru) Pa-ra-mác-tha" |
| Thỏ rơ-pai | wrong 60 target removed; the 87 target already existed |
| Thử thần và miêu thần | target added: 140 (tập IV), the Story itself, textName "Thử Thần và Miêu Thần" |
| Vè người hóa dế | 133 Khảo dị, textName "bài vè" (printed name kept, so searching "người hoá dế" still finds it) |
| Xử phiến đá | wrong 120 target removed; the 110 target already existed |

## Resolved by fuzzy match

Check each in-text spelling is really the same tale; fix or remove `textName` if not.

| Printed name | Qualifier | Story | Location | In-text spelling |
|---|---|---|---|---|
| Cây nêu và ngày Tết |  | 23 | khao-di | cây nêu ngày Tết |
| Cha để bán |  | 186 | khao-di | Của để bán |
| Cha mẹ nuôi con bể hồ lai láng, con nuôi cha mẹ kể tháng kể ngày |  | 51 | story | Cha mẹ nuôi con bể hồ lai láng con nuôi cha mẹ kể tháng kể ngày |
| Con vợ khôn lấy thằng chồng dại, như bông hoa lài cắm bãi cứt trâu |  | 47 | story | Con vợ khôn lấy thằng chồng dại như bông hoa lài  cắm bãi cứt trâu |
| Cô Mari ở túp lều trong rừng |  | 154 | khao-di | Cô Ma-ri ở túp lều trong rừng |
| Của trời trời lại lấy đi, giương đôi mắt ếch làm chi được trời |  | 61 | story | Của trời trời lại lấy đi giương đôi mắt ếch làm chi được trời |
| Gái ngoan dạy chồn | truyện Nam Trung Bộ | 90 | khao-di | Gái ngoan dạy chồng |
| Gầu Nà Gầu Rềnh |  | 12 | khao-di | Gầu Nà, Gầu Rềnh |
| Ha-rô-gô-mô hay là chiếc áo lông |  | 182 | khao-di | Ha-rô-gô-mô là chiếc áo lông |
| Hòn gạch nên vợ nên chồng |  | 41 | khao-di | Hòn gạch nên vợ chồng |
| Hồn Trương Ba da hàng thịt |  | 45 | story | Hồn Trương Ba, da hàng thịt |
| Nàng Can-tóc và Song Ang-cát |  | 154 | khao-di | Nàng Can-tóc và nàng Song Ang-cát |
| Người học trò ba con quỷ |  | 131 | story | Người học trò và ba con quỷ |
| Người vợ hi sinh cho thần Biển cứu chồng |  | 177 | khao-di | Người vợ hy sinh cho thần Biển cứu chồng |
| Nhà kiến trúc, vợ anh ta và ba vị đại thần của Gu-va-chia |  | 197 | khao-di | Nhà kiến trúc, vợ anh ta và ba vị đại nhân của vua Gu-va-chia |
| Ông Dài, ông Cộc hay là sự tích thần sông Kỳ cùng |  | 167 | story | Ông Dài ông Cộc hay là sự tích thần sông Kỳ-Cùng |
| Quan Âm Thị Kính, điệu kể hạnh |  | 176 | khao-di | Quan âm Thị Kính theo diệu kể hạnh |
| Sinh con rồi mới sinh cha, sinh cháu giữ nhà rồi mới sinh ông |  | 46 | story | Sinh con rồi mới sinh cha sinh cháu giữ nhà rồi mới sinh ông |
| Sóc lành, Sóc ác hay là Sự tích cây cỏ may |  | 150 | khao-di | Sóc-lành Sóc-ác hay là Sự tích cây cỏ may |
| Sự tích năm trâu sáu cột và chim bắt cô trói cột |  | 8 | story | Sự tích chim năm-trâu-sáu-cột và chim bắt-cô-trói-cột |
| Sự tích trầu cau và vôi | truyện Nghệ-an | 2 | khao-di | Sự tích trầu, cau và vôi |
| Sự tích vua Kơ-long Ga-rai xây tháp thi |  | 34 | khao-di | sự tích vua Kơ-long Gia-rai xây tháp thi |
| Túi tiền, cái còi và cái mũi |  | 165 | khao-di | Túi tiền, cái còi và cái mũ |
| Từ Đạo Hạnh hay là sự tích Thánh Láng |  | 120 | story | Từ Đạo Hạnh hay sự tích Thánh Láng |
| Ý Đớn Ý Đăm |  | 12 | khao-di | Ý Đớn, Ý Đăm |
| Ý Ưởi Ý Ót |  | 154 | khao-di | Ý Ưởi Ý Ôi |
