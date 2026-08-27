import hashlib
import sqlite3

biz = sqlite3.connect("decrypted/message/biz_message_0.db")
contact = sqlite3.connect("decrypted/contact/contact.db")
target = "Msg_76ef8bfa483737836dc48766b138a6fa"
for row in biz.execute("SELECT user_name, is_session FROM Name2Id"):
    u = row[0]
    t = "Msg_" + hashlib.md5(u.encode()).hexdigest()
    if t == target:
        nick = contact.execute("SELECT nick_name FROM contact WHERE username=?", (u,)).fetchone()
        print("owner:", u, nick, "is_session=", row[1])
