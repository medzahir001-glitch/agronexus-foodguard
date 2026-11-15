<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AgroNexus - FoodGuard</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',Arial,sans-serif}
  body{background:#F5F7F5;display:flex;min-height:100vh}
  /* SIDEBAR */
  .sidebar{width:230px;background:#fff;padding:20px;box-shadow:0 0 10px rgba(0,0,0,0.05)}
  .logo{font-size:26px;font-weight:900;color:#1B5E20;line-height:1}
  .logo span{font-size:15px;font-weight:600;color:#1B5E20;display:block}
  .menu{margin-top:30px;display:flex;flex-direction:column;gap:6px}
  .menu a{text-decoration:none;color:#212121;padding:12px 14px;border-radius:8px;font-weight:600}
  .menu a.active{background:#1B5E20;color:#fff}
  .menu a:hover{background:#E8F5E9}
  /* MAIN */
  .main{flex:1;padding:20px 28px}
  .top{display:flex;justify-content:space-between;align-items:center}
  .top h1{font-size:42px;color:#1B5E20}
  .top p{color:#555}
  .user{font-weight:700}
  .filter{background:#fff;padding:14px;border-radius:12px;display:flex;gap:14px;align-items:center;margin:16px 0;flex-wrap:wrap}
  .filter input{padding:10px 12px;border:1px solid #C8E6C9;border-radius:8px;outline:none}
  .btn{background:#1B5E20;color:#fff;border:none;padding:12px 18px;border-radius:8px;font-weight:800;cursor:pointer}
  /* CARDS */
  .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
  .card{background:#fff;padding:18px;border-radius:12px}
  .card small{color:#555;font-weight:600}
  .card h2{font-size:36px;color:#1B5E20;margin:6px 0}
  .card.red h2{color:#C62828}
  .card p{font-size:13px;color:#555}
  /* GRID */
  .grid{display:grid;grid-template-columns:1fr 1.6fr;gap:14px;margin-top:14px}
  .box{background:#fff;padding:18px;border-radius:12px}
  .box h3{color:#1B5E20;font-size:20px}
  .box p{color:#555;font-size:13px;margin-bottom:12px}
  .donut{width:140px;height:140px;border-radius:50%;background:conic-gradient(#1B5E20 0 78%, #C62828 78% 100%);display:flex;align-items:center;justify-content:center;margin:10px auto}
  .donut div{width:80px;height:80px;background:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:20px}
  .bar{display:flex;align-items:center;gap:8px;margin:6px 0;font-size:14px}
  .bar-fill{height:18px;background:#1B5E20;border-radius:4px}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{background:#E8F5E9;text-align:left;padding:10px}
  td{padding:10px;border-bottom:1px solid #eee}
  .ok{background:#E8F5E9;color:#1B5E20;padding:4px 8px;border-radius:20px;font-weight:700}
  .no{background:#FFEBEE;color:#C62828;padding:4px 8px;border-radius:20px;font-weight:700}
  .view{color:#1B5E20;font-weight:700;text-decoration:none}
  @media(max-width:900px){.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}.sidebar{display:none}}
</style>
</head>
<body>

<div class="sidebar">
  <div class="logo">AgroNexus<span>FoodGuard</span></div>
  <div class="menu">
    <a href="#" class="active">Dashboard</a>
    <a href="#">Products</a>
    <a href="#">Analyses</a>
    <a href="#">Reports</a>
    <a href="#">Quality Standards</a>
    <a href="#">Settings</a>
    <a href="#">Help & Support</a>
    <a href="#">Log out</a>
  </div>
</div>

<div class="main">
  <div class="top">
    <div><h1>Dashboard</h1><p>Monitoring agro-food quality & compliance in real time</p></div>
    <div class="user">MD Marine Dupont</div>
  </div>

  <div class="filter">
    <label><b>Date:</b></label><input type="date" value="2024-06-12">
    <label><b>Analyst:</b></label><input type="text" value="Marine Dupont">
    <button class="btn" onclick="alert('Analyse lancée !')">Run Analysis +</button>
  </div>

  <div class="cards">
    <div class="card"><small>Total Analyses</small><h2>142</h2><p>+12 this week</p></div>
    <div class="card"><small>Conforme</small><h2>111</h2><p>78% of total</p></div>
    <div class="card red"><small>Non Conforme</small><h2>31</h2><p>22% of total</p></div>
    <div class="card"><small>Pending Review</small><h2>8</h2><p>-3 since yesterday</p></div>
  </div>

  <div class="grid">
    <div>
      <div class="box">
        <h3>Conformity Rate</h3><p>Last 30 days • Updated today, 14:30</p>
        <div class="donut"><div>78%</div></div>
        <p style="text-align:center">● Conforme &nbsp; ● Non conforme</p>
      </div>
      <div class="box" style="margin-top:14px">
        <h3>Analyses by Product Category</h3>
        <div class="bar">Tomatoes <div class="bar-fill" style="width:120px"></div> 42</div>
        <div class="bar">Milk <div class="bar-fill" style="width:90px;opacity:.7"></div> 36</div>
        <div class="bar">Wheat <div class="bar-fill" style="width:70px;opacity:.6"></div> 28</div>
        <div class="bar">Cheese <div class="bar-fill" style="width:55px;opacity:.5"></div> 22</div>
        <div class="bar">Apples <div class="bar-fill" style="width:35px"></div> 14</div>
      </div>
    </div>

    <div class="box">
      <h3>Analysis History</h3><p>Latest product analyses</p>
      <table>
        <tr><th>Date</th><th>Sample ID</th><th>Product</th><th>Analyst</th><th>Result</th><th>Actions</th></tr>
        <tr><td>2024-06-12</td><td>SPL-2024-1187</td><td>Tomatoes — Batch T-204</td><td>Marine Dupont</td><td><span class="ok">Conforme</span></td><td><a class="view" href="#">View Details</a></td></tr>
        <tr><td>2024-06-12</td><td>SPL-2024-1186</td><td>Milk — Batch M-932</td><td>Marine Dupont</td><td><span class="no">Non conforme</span></td><td><a class="view" href="#">View Details</a></td></tr>
        <tr><td>2024-06-11</td><td>SPL-2024-1185</td><td>Wheat — Batch W-770</td><td>Marine Dupont</td><td><span class="ok">Conforme</span></td><td><a class="view" href="#">View Details</a></td></tr>
        <tr><td>2024-06-11</td><td>SPL-2024-1184</td><td>Cheese — Batch C-411</td><td>Nadia Kerrou</td><td><span class="no">Non conforme</span></td><td><a class="view" href="#">View Details</a></td></tr>
        <tr><td>2024-06-10</td><td>SPL-2024-1183</td><td>Apples — Batch A-055</td><td>Marine Dupont</td><td><span class="ok">Conforme</span></td><td><a class="view" href="#">View Details</a></td></tr>
      </table>
      <p style="margin-top:12px">Showing 5 of 142 results</p>
    </div>
  </div>
</div>

</body>
</html>
