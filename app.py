import os, sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, jsonify, render_template_string, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "development-only-change-this-secret")
DB = os.environ.get("DATABASE_PATH", "/data/companion.db")
os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)

STYLE = """
:root{--navy:#102c46;--blue:#1e527b;--ink:#172b3d;--muted:#71808d;--line:#e4e9ed;--pale:#f4f7f9}
*{box-sizing:border-box}body{margin:0;color:var(--ink);font-family:Arial,'Noto Sans TC',sans-serif}a{color:inherit;text-decoration:none}.wrap{max-width:1160px;margin:auto;padding:0 28px}
header{height:82px;display:flex;align-items:center;justify-content:space-between;padding:0 max(28px,calc((100vw - 1160px)/2));border-bottom:1px solid var(--line);background:white}
.brand{font-weight:800;letter-spacing:2px;color:var(--navy);font-size:16px}.brand small{display:block;font-size:8px;color:#83909a;margin-top:4px}
nav{display:flex;gap:28px;align-items:center;font-size:13px;color:#4a5a67}nav a:hover{color:var(--blue)}.cta,.btn{background:var(--navy);color:white;padding:14px 20px;display:inline-block;border:0;cursor:pointer}
.hero{background:linear-gradient(110deg,#102c46,#1a496c);color:white;padding:110px 0 100px;min-height:510px}.eyebrow{font-size:10px;letter-spacing:2px;color:#9fb7c8;font-weight:bold}
h1{font-size:54px;line-height:1.35;margin:26px 0 18px}h1 em{font-style:normal;color:#a9c6d9}.hero p{color:#d3dee6;line-height:2;max-width:650px}
.section{padding:86px 0}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px}.card{border-top:1px solid #dce3e8;padding:26px 12px 26px 0}.card h3{font-size:17px}.card p,.muted{color:var(--muted);line-height:1.9;font-size:13px}
h2{font-size:32px;line-height:1.5;color:var(--navy)}.split{display:grid;grid-template-columns:1fr 1fr;gap:80px}
footer{background:#0b2135;color:#b4c3ce;padding:40px 0;font-size:12px;margin-top:40px}
.formbox{max-width:720px;background:#f5f7f9;padding:32px;margin:40px auto}label{display:block;font-size:13px;margin:14px 0}input,select,textarea{display:block;width:100%;padding:12px;border:1px solid #ccd5dc;margin-top:7px;font:inherit;background:white}.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:12px;border-bottom:1px solid var(--line);text-align:left}small{color:var(--muted)}
.flash{padding:12px;margin:12px auto;max-width:1100px;background:#eef6f0}
@media(max-width:760px){header{height:auto;padding:20px;display:block}nav{flex-wrap:wrap;gap:14px;margin-top:16px}h1{font-size:38px}.grid,.split,.row{grid-template-columns:1fr}.section{padding:55px 0}}
"""
BASE = """<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}}｜Companion</title><style>""" + STYLE + """</style><body><header><a class="brand" href="/">COMPANION<small>GLOBAL STAY PARTNERS</small></a><nav><a href="/">首頁</a><a href="/about">關於我們</a><a href="/services">合作服務</a><a href="/supplier/login">供應商入口</a><a class="cta" href="/contact">商業合作洽詢 ↗</a></nav></header>{% with ms=get_flashed_messages() %}{% for m in ms %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}<main>{{body|safe}}</main><footer><div class="wrap">© {{year}} Companion. All rights reserved.　全球住宿商業合作平台</div></footer></body></html>"""
SERVICES=[("全球住宿資源整合","串聯多元住宿供應商與目的地資源，建立更完整的住宿採購網絡。"),("預訂 API 技術串接","透過標準化技術介面，協助合作夥伴整合搜尋、報價與預訂流程。"),("跨境商務合作","支援不同市場的商務需求，協助合作夥伴拓展國際客源與通路。"),("品質與營運支援","重視住宿資訊品質、服務流程與合作管理，建立長期互信關係。")]

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT);
  CREATE TABLE IF NOT EXISTS inquiries(id INTEGER PRIMARY KEY,company TEXT,contact TEXT,email TEXT,phone TEXT,interest TEXT,message TEXT,created_at TEXT,status TEXT DEFAULT 'new');
  CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY,company TEXT,contact TEXT,email TEXT UNIQUE,password_hash TEXT,created_at TEXT);
  CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY,supplier_id INTEGER,name TEXT,city TEXT,country TEXT,kind TEXT,rooms INTEGER,description TEXT,status TEXT DEFAULT 'pending',created_at TEXT);''')
  u=os.getenv("ADMIN_USERNAME","admin"); p=os.getenv("ADMIN_PASSWORD","ChangeMe123!")
  if not c.execute("select id from admins where username=?",(u,)).fetchone():
   c.execute("insert into admins(username,password_hash) values(?,?)",(u,generate_password_hash(p)))
init()

def page(title,body): return render_template_string(BASE,title=title,body=body,year=datetime.now().year)
def admin(fn):
 @wraps(fn)
 def w(*a,**k):
  if not session.get("admin"): return redirect("/admin/login")
  return fn(*a,**k)
 return w
def supplier(fn):
 @wraps(fn)
 def w(*a,**k):
  if not session.get("supplier"): return redirect("/supplier/login")
  return fn(*a,**k)
 return w

@app.get("/")
def home():
 cards="".join(f'<article class="card"><small>0{i}</small><h3>{n}</h3><p>{d}</p></article>' for i,(n,d) in enumerate(SERVICES,1))
 body=f'''<section class="hero"><div class="wrap"><div class="eyebrow">GLOBAL ACCOMMODATION PARTNERSHIP</div><h1>讓全球住宿資源<br><em>連結更多可能</em></h1><p>Companion 致力於串聯全球住宿供應資源與商業夥伴，以技術、服務與合作網絡，打造高效率的跨境住宿生態系。</p><a class="btn" href="/contact">探索合作機會 ↗</a></div></section><section class="wrap section"><div class="split"><h2>不只是住宿媒合，<br>更是值得信賴的合作夥伴。</h2><p class="muted">面對快速變化的全球旅遊市場，合作需要的不只是資源，更需要穩定的技術、清晰的流程與長期互信。Companion 以整合思維連結住宿供應商、通路與企業夥伴。</p></div><h2>讓合作，從資源到技術全面接軌。</h2><div class="grid">{cards}</div></section>'''
 return page("全球住宿商業合作",body)
@app.get("/about")
def about(): return page("關於我們",'<section class="wrap section"><div class="eyebrow">ABOUT COMPANION</div><h1 style="color:#102c46">連結全球住宿資源，<em>創造合作價值。</em></h1><p class="muted">Companion 致力於串聯住宿供應商、旅遊通路與企業夥伴，透過資源整合與技術合作，建立長期互信的商務網絡。</p></section>')
@app.get("/services")
def services():
 rows="".join(f'<article class="card"><h2>{n}</h2><p>{d}</p></article>' for n,d in SERVICES)
 return page("合作服務",f'<section class="wrap section"><h1 style="color:#102c46">從資源整合到技術串接</h1><div class="grid">{rows}</div></section>')
@app.get("/contact")
def contact():
 body='''<section class="wrap section"><h1 style="color:#102c46">讓我們聊聊，<em>如何創造下一個合作機會。</em></h1><p class="muted">請留下聯絡資訊與合作方向，我們將進一步了解需求。</p><form class="formbox" method="post"><div class="row"><label>公司／機構名稱 *<input name="company" required></label><label>聯絡人姓名 *<input name="contact" required></label></div><div class="row"><label>電子郵件 *<input type="email" name="email" required></label><label>聯絡電話<input name="phone"></label></div><label>合作需求<select name="interest"><option>住宿資源供應</option><option>預訂 API 串接</option><option>旅遊通路合作</option><option>企業／其他商務合作</option></select></label><label>需求說明<textarea name="message" rows="5"></textarea></label><button class="btn">送出合作需求 ↗</button></form></section>'''
 return page("商業合作洽詢",body)
@app.post("/contact")
def contact_post():
 d=request.form
 if not d.get("company") or not d.get("contact") or "@" not in d.get("email",""): flash("請填寫完整且有效的聯絡資料。")
 else:
  with conn() as c: c.execute("insert into inquiries(company,contact,email,phone,interest,message,created_at) values(?,?,?,?,?,?,?)",(d["company"],d["contact"],d["email"],d.get("phone",""),d.get("interest",""),d.get("message",""),datetime.now().isoformat()))
  flash("已收到您的合作需求，謝謝。")
 return redirect("/contact")
@app.get("/health")
def health(): return jsonify(status="ok",service="Companion")
@app.get("/api/properties")
def api_properties():
 with conn() as c: rows=c.execute("select id,name,city,country,kind,rooms,description from properties where status='approved' order by id desc").fetchall()
 return jsonify(data=[dict(x) for x in rows],count=len(rows))
@app.route("/supplier/register",methods=["GET","POST"])
def register():
 if request.method=="GET": return page("供應商註冊",'<section class="formbox"><h2>建立供應商帳號</h2><form method="post"><label>公司名稱<input name="company" required></label><label>聯絡人<input name="contact" required></label><label>電子郵件<input name="email" type="email" required></label><label>密碼（至少10字元）<input name="password" type="password" minlength="10" required></label><button class="btn">註冊</button></form></section>')
 d=request.form
 if len(d.get("password",""))<10: flash("密碼至少需要 10 個字元。"); return redirect("/supplier/register")
 try:
  with conn() as c: c.execute("insert into suppliers(company,contact,email,password_hash,created_at) values(?,?,?,?,?)",(d["company"],d["contact"],d["email"].lower(),generate_password_hash(d["password"]),datetime.now().isoformat()))
 except sqlite3.IntegrityError: flash("此電子郵件已註冊。"); return redirect("/supplier/login")
 flash("註冊成功，請登入。"); return redirect("/supplier/login")
@app.route("/supplier/login",methods=["GET","POST"])
def supplier_login():
 if request.method=="GET": return page("供應商登入",'<section class="formbox"><h2>供應商登入</h2><form method="post"><label>電子郵件<input name="email" type="email" required></label><label>密碼<input name="password" type="password" required></label><button class="btn">登入</button></form><p><a href="/supplier/register">建立供應商帳號</a></p></section>')
 with conn() as c: s=c.execute("select * from suppliers where email=?",(request.form["email"].lower(),)).fetchone()
 if s and check_password_hash(s["password_hash"],request.form["password"]): session.clear(); session["supplier"]=s["id"]; return redirect("/supplier")
 flash("電子郵件或密碼錯誤。"); return redirect("/supplier/login")
@app.get("/supplier")
@supplier
def supplier_home():
 with conn() as c: ps=c.execute("select * from properties where supplier_id=? order by id desc",(session["supplier"],)).fetchall()
 rows="".join(f'<tr><td>{p["name"]}</td><td>{p["city"]}，{p["country"]}</td><td>{p["status"]}</td></tr>' for p in ps)
 return page("供應商中心",f'''<section class="wrap section"><h2>供應商會員中心</h2><form class="formbox" method="post" action="/supplier/add"><label>住宿名稱<input name="name" required></label><div class="row"><label>國家<input name="country" required></label><label>城市<input name="city" required></label></div><label>住宿類型<input name="kind" required></label><label>房間數<input type="number" name="rooms" value="1" min="1"></label><label>住宿介紹<textarea name="description"></textarea></label><button class="btn">提交房源審核</button></form><h2>我的房源</h2><table><tr><th>名稱</th><th>地點</th><th>狀態</th></tr>{rows}</table><form method="post" action="/logout"><button class="btn">登出</button></form></section>''')
@app.post("/supplier/add")
@supplier
def supplier_add():
 d=request.form
 with conn() as c: c.execute("insert into properties(supplier_id,name,city,country,kind,rooms,description,created_at) values(?,?,?,?,?,?,?,?)",(session["supplier"],d["name"],d["city"],d["country"],d["kind"],max(1,int(d.get("rooms",1))),d.get("description",""),datetime.now().isoformat()))
 flash("房源已提交，等待審核。"); return redirect("/supplier")
@app.post("/logout")
def logout(): session.clear(); return redirect("/")
@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
 if request.method=="GET": return page("管理員登入",'<section class="formbox"><h2>管理員登入</h2><form method="post"><label>帳號<input name="username" required></label><label>密碼<input name="password" type="password" required></label><button class="btn">登入</button></form></section>')
 with conn() as c: a=c.execute("select * from admins where username=?",(request.form["username"],)).fetchone()
 if a and check_password_hash(a["password_hash"],request.form["password"]): session.clear(); session["admin"]=a["id"]; return redirect("/admin")
 flash("帳號或密碼錯誤。"); return redirect("/admin/login")
@app.get("/admin")
@admin
def admin_home():
 with conn() as c:
  qs=c.execute("select * from inquiries order by id desc").fetchall(); ps=c.execute("select p.*,s.company from properties p join suppliers s on s.id=p.supplier_id order by p.id desc").fetchall()
 qrows="".join(f'<tr><td>{q["company"]}</td><td>{q["contact"]}</td><td>{q["email"]}</td><td>{q["created_at"]}</td></tr>' for q in qs)
 prows="".join(f'<tr><td>{p["name"]}</td><td>{p["company"]}</td><td>{p["city"]},{p["country"]}</td><td><form method="post" action="/admin/property/{p["id"]}"><select name="status"><option value="pending">待審核</option><option value="approved">核准</option><option value="rejected">退回</option></select><button>更新</button></form></td></tr>' for p in ps)
 return page("管理後台",f'<section class="wrap section"><h2>合作洽詢</h2><table><tr><th>公司</th><th>聯絡人</th><th>電郵</th><th>時間</th></tr>{qrows}</table><h2>房源審核</h2><table><tr><th>房源</th><th>供應商</th><th>地點</th><th>審核</th></tr>{prows}</table><form method="post" action="/logout"><button class="btn">登出</button></form></section>')
@app.post("/admin/property/<int:pid>")
@admin
def review(pid):
 st=request.form.get("status")
 if st not in ("pending","approved","rejected"): abort(400)
 with conn() as c: c.execute("update properties set status=? where id=?",(st,pid))
 return redirect("/admin")
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
