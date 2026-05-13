# PHÁT HIỆN LỖI - Cần sửa

## 1. Lỗi `assigned_to` KHÔNG TỒN TẠI trong model SubTask
Model `SubTask` dùng `assigned_users` (many-to-many), KHÔNG có `assigned_to` column
- app.py dòng 911, 1169, 1355: `SubTask.assigned_to` → phải đổi thành `SubTask.assigned_users.any(User.id == ...)`
- app.py dòng 1001, 1003, 1195, 1198: `s.assigned_user` → phải đổi thành `s.assigned_users`

## 2. Lỗi `assigned_user` (số ít) không tồn tại
- app.py dòng 462: `assigned = subtask.assigned_user` → sai
- app.py dòng 1173: `selectinload(SubTask.assigned_user)` → sai

## 3. Lỗi template `subtask_detail.html` dòng 17-21
Dùng `subtask.assigned_user` nhưng model có `assigned_users` (many-to-many)

## 4. Lỗi `approve_delete()` double-check role thiếu
app.py dòng 2363 và 2371: check role 2 lần mâu thuẫn