import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import secrets
from bot import Group, UserRank, SubCode, Base, RANKS, PLANS, DEVELOPER_ID

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", secrets.token_hex(16))
engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///rayo_protect.db"))
Session = sessionmaker(bind=engine)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "abdulrahman2006")

@app.route('/')
def index():
    if 'logged_in' not in session: return redirect(url_for('login'))
    db_session = Session()
    total_groups = db_session.query(Group).count()
    active_groups = db_session.query(Group).filter(Group.is_active == True, Group.expiry_date > datetime.now()).count()
    total_codes = db_session.query(SubCode).count()
    used_codes = db_session.query(SubCode).filter_by(is_used=True).count()
    groups = db_session.query(Group).order_by(Group.id.desc()).limit(10).all()
    db_session.close()
    return render_template('dashboard.html', total_groups=total_groups, active_groups=active_groups, total_codes=total_codes, used_codes=used_codes, groups=groups, ranks=RANKS, plans=PLANS, now=datetime.now())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error='باسورد غلط')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/groups')
def groups():
    if 'logged_in' not in session: return redirect(url_for('login'))
    db_session = Session()
    all_groups = db_session.query(Group).order_by(Group.expiry_date.desc()).all()
    db_session.close()
    return render_template('groups.html', groups=all_groups, ranks=RANKS, plans=PLANS, now=datetime.now())

@app.route('/codes')
def codes():
    if 'logged_in' not in session: return redirect(url_for('login'))
    db_session = Session()
    all_codes = db_session.query(SubCode).order_by(SubCode.created_at.desc()).all()
    db_session.close()
    return render_template('codes.html', codes=all_codes, plans=PLANS)

@app.route('/ranks/<int:group_id>')
def group_ranks(group_id):
    if 'logged_in' not in session: return redirect(url_for('login'))
    db_session = Session()
    group = db_session.query(Group).filter_by(group_id=group_id).first()
    if not group: 
        db_session.close()
        return "الجروب مش موجود", 404
    ranks = db_session.query(UserRank).filter_by(group_id=group_id).order_by(UserRank.rank.desc()).all()
    db_session.close()
    return render_template('ranks.html', group=group, ranks=ranks, ranks_dict=RANKS)

@app.route('/api/generate_code/<plan>')
def api_generate_code(plan):
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    if plan not in PLANS: return jsonify({"error": "Invalid plan"}), 400
    import random, string
    code = f"RAYO-{plan.upper()}-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    db_session = Session()
    new_code = SubCode(code=code, plan=plan)
    db_session.add(new_code)
    db_session.commit()
    db_session.close()
    return jsonify({"code": code, "plan": PLANS['name']})

@app.route('/api/toggle_group/<int:group_id>')
def api_toggle_group(group_id):
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    db_session = Session()
    group = db_session.query(Group).filter_by(group_id=group_id).first()
    if group:
        group.is_active = not group.is_active
        db_session.commit()
        status = "مفعل" if group.is_active else "موقوف"
        db_session.close()
        return jsonify({"status": status})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/extend_sub/<int:group_id>/<int:days>')
def api_extend_sub(group_id, days):
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    db_session = Session()
    group = db_session.query(Group).filter_by(group_id=group_id).first()
    if group:
        if group.expiry_date and group.expiry_date > datetime.now():
            group.expiry_date += timedelta(days=days)
        else:
            group.expiry_date = datetime.now() + timedelta(days=days)
        group.is_active = True
        db_session.commit()
        db_session.close()
        return jsonify({"success": True, "new_date": group.expiry_date.strftime('%Y-%m-%d')})
    return jsonify({"error": "Not found"}), 404

@app.route('/api/set_rank', methods=['POST'])
def api_set_rank():
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    group_id = int(data['group_id'])
    user_id = int(data['user_id'])
    new_rank = int(data['rank'])
    db_session = Session()
    user_rank = db_session.query(UserRank).filter_by(group_id=group_id, user_id=user_id).first()
    if not user_rank:
        user_rank = UserRank(group_id=group_id, user_id=user_id, rank=new_rank)
        db_session.add(user_rank)
    else:
        user_rank.rank = new_rank
    db_session.commit()
    db_session.close()
    return jsonify({"success": True, "rank_name": RANKS[new_rank]})

@app.route('/api/remove_rank', methods=['POST'])
def api_remove_rank():
    if 'logged_in' not in session: return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    group_id = int(data['group_id'])
    user_id = int(data['user_id'])
    db_session = Session()
    db_session.query(UserRank).filter_by(group_id=group_id, user_id=user_id).delete()
    db_session.commit()
    db_session.close()
    return jsonify({"success": True})
