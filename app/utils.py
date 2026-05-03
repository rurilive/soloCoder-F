import io
import base64
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import qrcode
from PIL import Image
from user_agents import parse

def generate_qr_code(data: str, size: int = 10) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

def parse_user_agent(user_agent_string: str) -> Dict[str, str]:
    result = {
        'device_type': 'Unknown',
        'browser': 'Unknown',
        'os': 'Unknown'
    }
    
    if not user_agent_string:
        return result
    
    try:
        user_agent = parse(user_agent_string)
        
        if user_agent.is_mobile:
            result['device_type'] = 'Mobile'
        elif user_agent.is_tablet:
            result['device_type'] = 'Tablet'
        elif user_agent.is_pc:
            result['device_type'] = 'Desktop'
        else:
            result['device_type'] = 'Other'
        
        if user_agent.browser.family != 'Other':
            result['browser'] = user_agent.browser.family
            if user_agent.browser.version_string:
                result['browser'] += f' {user_agent.browser.version_string}'
        
        if user_agent.os.family != 'Other':
            result['os'] = user_agent.os.family
            if user_agent.os.version_string:
                result['os'] += f' {user_agent.os.version_string}'
    
    except Exception:
        pass
    
    return result

def get_client_ip(request) -> str:
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip = forwarded_for.split(',')[0].strip()
        return ip
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    return request.remote_addr or '127.0.0.1'

def is_valid_url(url: str) -> bool:
    if not url:
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_location_from_ip(ip: str) -> Dict[str, Optional[str]]:
    return {
        'country': None,
        'region': None,
        'city': None
    }
