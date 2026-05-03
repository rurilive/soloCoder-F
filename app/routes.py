from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, make_response, current_app
from app import db, allowed_file
from app.models import QRCode, ScanRecord
from app.utils import (
    generate_qr_code, 
    parse_user_agent, 
    get_client_ip, 
    is_valid_url, 
    get_location_from_ip, 
    get_available_styles,
    generate_qr_with_logo,
    generate_qr_on_background,
    generate_artistic_qr,
    image_to_base64,
    base64_to_image
)
from datetime import datetime, timedelta
from collections import Counter
import io
import os
import base64
import uuid
from werkzeug.utils import secure_filename
from PIL import Image

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
    
    available_styles = get_available_styles()
    
    return render_template(
        'detail.html',
        qr_code=qr_code,
        qr_image=qr_image,
        short_url=short_url,
        scan_records=scan_records[:50],
        device_counts=dict(device_counts),
        browser_counts=dict(browser_counts),
        country_counts=dict(country_counts),
        last_7_days=last_7_days,
        available_styles=available_styles
    )


@main.route('/api/qr/<int:qr_id>/style/<style_name>')
def get_qr_with_style(qr_id, style_name):
    qr_code = QRCode.query.get_or_404(qr_id)
    short_url = url_for('main.redirect_short', short_code=qr_code.short_code, _external=True)
    
    available_styles = get_available_styles()
    if style_name not in available_styles:
        return jsonify({'error': 'Invalid style name'}), 400
    
    qr_image = generate_qr_code(short_url, style=style_name)
    
    return jsonify({
        'success': True,
        'style': style_name,
        'style_info': available_styles[style_name],
        'qr_image': qr_image
    })


@main.route('/api/qr/<int:qr_id>/download/<style_name>')
def download_qr_with_style(qr_id, style_name):
    qr_code = QRCode.query.get_or_404(qr_id)
    short_url = url_for('main.redirect_short', short_code=qr_code.short_code, _external=True)
    
    available_styles = get_available_styles()
    if style_name not in available_styles:
        return jsonify({'error': 'Invalid style name'}), 400
    
    qr_image = generate_qr_code(short_url, style=style_name, size=15)
    
    img_data = base64.b64decode(qr_image.split(',')[1])
    
    response = make_response(img_data)
    response.headers.set('Content-Type', 'image/png')
    response.headers.set(
        'Content-Disposition', 
        'attachment', 
        filename=f'{qr_code.name}_{style_name}.png'
    )
    
    return response


@main.route('/api/qr/styles')
def list_qr_styles():
    available_styles = get_available_styles()
    return jsonify({
        'success': True,
        'styles': available_styles
    })

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


@main.route('/api/upload/image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    try:
        img = Image.open(file)
        img.verify()
        file.seek(0)
        img = Image.open(file)
        
        max_size = 2048
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        img_base64 = image_to_base64(img)
        
        preview_size = 200
        preview_img = img.copy()
        if preview_img.width > preview_size or preview_img.height > preview_size:
            ratio = min(preview_size / preview_img.width, preview_size / preview_img.height)
            new_size = (int(preview_img.width * ratio), int(preview_img.height * ratio))
            preview_img = preview_img.resize(new_size, Image.Resampling.LANCZOS)
        
        preview_base64 = image_to_base64(preview_img)
        
        return jsonify({
            'success': True,
            'image': img_base64,
            'preview': preview_base64,
            'width': img.width,
            'height': img.height
        })
        
    except Exception as e:
        return jsonify({'error': f'Invalid image file: {str(e)}'}), 400


@main.route('/api/qr/<int:qr_id>/with-logo', methods=['POST'])
def generate_qr_logo(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    short_url = url_for('main.redirect_short', short_code=qr_code.short_code, _external=True)
    
    data = request.get_json()
    
    if not data or 'logo_image' not in data:
        return jsonify({'error': 'Logo image is required'}), 400
    
    try:
        logo_img = base64_to_image(data['logo_image'])
    except Exception as e:
        return jsonify({'error': f'Invalid logo image: {str(e)}'}), 400
    
    style = data.get('style', 'classic')
    logo_size_ratio = float(data.get('logo_size_ratio', 0.25))
    logo_round = data.get('logo_round', True)
    logo_border = data.get('logo_border', True)
    logo_border_color = tuple(data.get('logo_border_color', [255, 255, 255]))
    logo_border_width = int(data.get('logo_border_width', 4))
    
    try:
        qr_image = generate_qr_with_logo(
            data=short_url,
            logo_image=logo_img,
            size=10,
            style=style,
            logo_size_ratio=logo_size_ratio,
            logo_round=logo_round,
            logo_border=logo_border,
            logo_border_color=logo_border_color,
            logo_border_width=logo_border_width
        )
        
        return jsonify({
            'success': True,
            'qr_image': qr_image,
            'style': style,
            'options': {
                'logo_size_ratio': logo_size_ratio,
                'logo_round': logo_round,
                'logo_border': logo_border
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate QR code: {str(e)}'}), 500


@main.route('/api/qr/<int:qr_id>/on-background', methods=['POST'])
def generate_qr_background(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    short_url = url_for('main.redirect_short', short_code=qr_code.short_code, _external=True)
    
    data = request.get_json()
    
    if not data or 'background_image' not in data:
        return jsonify({'error': 'Background image is required'}), 400
    
    try:
        bg_img = base64_to_image(data['background_image'])
    except Exception as e:
        return jsonify({'error': f'Invalid background image: {str(e)}'}), 400
    
    style = data.get('style', 'classic')
    qr_position = data.get('qr_position', 'center')
    qr_size_ratio = float(data.get('qr_size_ratio', 0.6))
    qr_opacity = float(data.get('qr_opacity', 1.0))
    qr_padding = int(data.get('qr_padding', 20))
    
    qr_bg_enabled = data.get('qr_background_enabled', True)
    if qr_bg_enabled:
        qr_bg_color = tuple(data.get('qr_background_color', [255, 255, 255, 200]))
    else:
        qr_bg_color = None
    
    try:
        qr_image = generate_qr_on_background(
            data=short_url,
            background_image=bg_img,
            size=10,
            style=style,
            qr_position=qr_position,
            qr_size_ratio=qr_size_ratio,
            qr_opacity=qr_opacity,
            qr_padding=qr_padding,
            qr_background=qr_bg_color
        )
        
        return jsonify({
            'success': True,
            'qr_image': qr_image,
            'style': style,
            'options': {
                'qr_position': qr_position,
                'qr_size_ratio': qr_size_ratio,
                'qr_opacity': qr_opacity
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate QR code: {str(e)}'}), 500


@main.route('/api/qr/<int:qr_id>/artistic', methods=['POST'])
def generate_qr_artistic(qr_id):
    qr_code = QRCode.query.get_or_404(qr_id)
    short_url = url_for('main.redirect_short', short_code=qr_code.short_code, _external=True)
    
    data = request.get_json()
    
    if not data or 'art_image' not in data:
        return jsonify({'error': 'Art image is required'}), 400
    
    try:
        art_img = base64_to_image(data['art_image'])
    except Exception as e:
        return jsonify({'error': f'Invalid art image: {str(e)}'}), 400
    
    style = data.get('style', 'classic')
    blend_mode = data.get('blend_mode', 'overlay')
    qr_opacity = float(data.get('qr_opacity', 0.7))
    art_opacity = float(data.get('art_opacity', 0.3))
    
    qr_color_override = data.get('qr_color_override')
    if qr_color_override:
        qr_color_override = tuple(qr_color_override)
    
    try:
        qr_image = generate_artistic_qr(
            data=short_url,
            art_image=art_img,
            size=10,
            style=style,
            blend_mode=blend_mode,
            qr_opacity=qr_opacity,
            art_opacity=art_opacity,
            qr_color_override=qr_color_override
        )
        
        return jsonify({
            'success': True,
            'qr_image': qr_image,
            'style': style,
            'options': {
                'blend_mode': blend_mode,
                'qr_opacity': qr_opacity,
                'art_opacity': art_opacity
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate QR code: {str(e)}'}), 500


@main.route('/api/qr/<int:qr_id>/download-custom', methods=['POST'])
def download_custom_qr(qr_id):
    data = request.get_json()
    
    if not data or 'qr_image' not in data:
        return jsonify({'error': 'QR image data is required'}), 400
    
    try:
        qr_img_data = data['qr_image']
        qr_code = QRCode.query.get_or_404(qr_id)
        
        img = base64_to_image(qr_img_data)
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_data = buffered.getvalue()
        
        response = make_response(img_data)
        response.headers.set('Content-Type', 'image/png')
        response.headers.set(
            'Content-Disposition',
            'attachment',
            filename=f'{qr_code.name}_custom.png'
        )
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Failed to download: {str(e)}'}), 500


@main.route('/api/embed/modes')
def get_embed_modes():
    modes = [
        {
            'id': 'logo',
            'name': '中心Logo',
            'description': '将Logo图片嵌入到二维码中心位置',
            'icon': '🔵'
        },
        {
            'id': 'background',
            'name': '背景嵌入',
            'description': '将二维码叠加到背景图片上',
            'icon': '🖼️'
        },
        {
            'id': 'artistic',
            'name': '艺术融合',
            'description': '将二维码与图片进行艺术化融合',
            'icon': '🎨'
        }
    ]
    
    positions = [
        {'id': 'center', 'name': '居中'},
        {'id': 'top_left', 'name': '左上'},
        {'id': 'top_right', 'name': '右上'},
        {'id': 'bottom_left', 'name': '左下'},
        {'id': 'bottom_right', 'name': '右下'}
    ]
    
    blend_modes = [
        {'id': 'overlay', 'name': '叠加', 'description': '简单的透明度叠加'},
        {'id': 'multiply', 'name': '正片叠底', 'description': '保留图片暗部作为二维码颜色'},
        {'id': 'colorize', 'name': '着色', 'description': '用图片颜色替换二维码颜色'},
        {'id': 'silhouette', 'name': '剪影', 'description': '二维码白色部分镂空，显示背景图片'}
    ]
    
    return jsonify({
        'success': True,
        'modes': modes,
        'positions': positions,
        'blend_modes': blend_modes
    })
