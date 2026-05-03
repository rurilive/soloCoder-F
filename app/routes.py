from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from app import db
from app.models import QRCode, ScanRecord
from app.utils import generate_qr_code, parse_user_agent, get_client_ip, is_valid_url, get_location_from_ip
from datetime import datetime, timedelta
from collections import Counter

main = Blueprint('main', __name__)

@main.route('/')
def index():
    qr_codes = QRCode.query.order_by(QRCode.created_at.desc()).all()
    return render_template('index.html', qr_codes=qr_codes)

@main.route('/create', methods=['POST'])
def create_qr():
    name = request.form.get('name', '').strip()
    target_url = request.form.get('target_url', '').strip()
    
    if not name:
        flash('请输入二维码名称', 'error')
        return redirect(url_for('main.index'))
    
    if not target_url or not is_valid_url(target_url):
        flash('请输入有效的URL地址', 'error')
        return redirect(url_for('main.index'))
    
    qr_code = QRCode(name=name, target_url=target_url)
    db.session.add(qr_code)
    db.session.commit()
    
    flash('二维码创建成功', 'success')
    return redirect(url_for('main.index'))

@main.route('/qr/<int:qr_id>')
def qr_detail(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    
    short_url = url_for('main.redirect_short', short_code=qr_code.short_code, _external=True)
    qr_image = generate_qr_code(short_url)
    
    scan_records = ScanRecord.query.filter_by(qr_code_id=qr_id).order_by(ScanRecord.scanned_at.desc()).all()
    
    device_counts = Counter(r.device_type for r in scan_records if r.device_type)
    browser_counts = Counter(r.browser for r in scan_records if r.browser)
    country_counts = Counter(r.country for r in scan_records if r.country)
    
    today = datetime.utcnow().date()
    last_7_days = {}
    for i in range(7):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        count = ScanRecord.query.filter(
            ScanRecord.qr_code_id == qr_id,
            db.func.date(ScanRecord.scanned_at) == date_str
        ).count()
        last_7_days[date_str] = count
    
    last_7_days = dict(sorted(last_7_days.items()))
    
    return render_template(
        'detail.html',
        qr_code=qr_code,
        qr_image=qr_image,
        short_url=short_url,
        scan_records=scan_records[:50],
        device_counts=dict(device_counts),
        browser_counts=dict(browser_counts),
        country_counts=dict(country_counts),
        last_7_days=last_7_days
    )

@main.route('/delete/<int:qr_id>', methods=['POST'])
def delete_qr(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    db.session.delete(qr_code)
    db.session.commit()
    flash('二维码已删除', 'success')
    return redirect(url_for('main.index'))

@main.route('/toggle/<int:qr_id>', methods=['POST'])
def toggle_qr(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    qr_code.is_active = not qr_code.is_active
    db.session.commit()
    
    status = '已启用' if qr_code.is_active else '已禁用'
    flash(f'二维码{status}', 'success')
    return redirect(url_for('main.qr_detail', qr_id=qr_id))

@main.route('/r/<short_code>')
def redirect_short(short_code):
    qr_code = QRCode.query.filter_by(short_code=short_code).first_or_404()
    
    if not qr_code.is_active:
        return "此二维码已被禁用", 403
    
    ip_address = get_client_ip(request)
    user_agent_string = request.headers.get('User-Agent', '')
    
    ua_info = parse_user_agent(user_agent_string)
    location = get_location_from_ip(ip_address)
    
    scan_record = ScanRecord(
        qr_code_id=qr_code.id,
        ip_address=ip_address,
        country=location.get('country'),
        region=location.get('region'),
        city=location.get('city'),
        device_type=ua_info.get('device_type'),
        browser=ua_info.get('browser'),
        os=ua_info.get('os'),
        user_agent=user_agent_string[:500]
    )
    db.session.add(scan_record)
    db.session.commit()
    
    return redirect(qr_code.target_url)

@main.route('/api/qr/<int:qr_id>/stats')
def api_qr_stats(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    
    scan_records = ScanRecord.query.filter_by(qr_code_id=qr_id).all()
    
    device_counts = Counter(r.device_type for r in scan_records if r.device_type)
    browser_counts = Counter(r.browser for r in scan_records if r.browser)
    country_counts = Counter(r.country for r in scan_records if r.country)
    
    return jsonify({
        'qr_code': qr_code.to_dict(),
        'stats': {
            'total_scans': len(scan_records),
            'devices': dict(device_counts),
            'browsers': dict(browser_counts),
            'countries': dict(country_counts)
        }
    })
