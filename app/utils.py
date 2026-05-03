import io
import base64
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlparse
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer, 
    GappedSquareModuleDrawer,
    CircleModuleDrawer,
    RoundedModuleDrawer,
    VerticalBarsDrawer,
    HorizontalBarsDrawer
)
from qrcode.image.styles.colormasks import (
    SolidFillColorMask,
    RadialGradiantColorMask,
    SquareGradiantColorMask,
    HorizontalGradiantColorMask,
    VerticalGradiantColorMask
)
from PIL import Image, ImageDraw
from user_agents import parse


QR_STYLES = {
    'classic': {
        'name': '经典黑白',
        'description': '传统的黑白二维码，兼容性最好',
        'module_drawer': 'square',
        'color_mask': 'solid',
        'colors': {'front': (0, 0, 0), 'back': (255, 255, 255)}
    },
    'blue_white': {
        'name': '蓝白简约',
        'description': '蓝色前景，白色背景',
        'module_drawer': 'square',
        'color_mask': 'solid',
        'colors': {'front': (66, 133, 244), 'back': (255, 255, 255)}
    },
    'green_white': {
        'name': '清新绿色',
        'description': '绿色前景，白色背景',
        'module_drawer': 'square',
        'color_mask': 'solid',
        'colors': {'front': (52, 168, 83), 'back': (255, 255, 255)}
    },
    'purple_white': {
        'name': '紫色优雅',
        'description': '紫色前景，白色背景',
        'module_drawer': 'square',
        'color_mask': 'solid',
        'colors': {'front': (147, 51, 234), 'back': (255, 255, 255)}
    },
    'dark_mode': {
        'name': '深色模式',
        'description': '白色前景，深色背景',
        'module_drawer': 'square',
        'color_mask': 'solid',
        'colors': {'front': (255, 255, 255), 'back': (30, 30, 40)}
    },
    'rounded': {
        'name': '圆角方形',
        'description': '圆角模块，更加柔和',
        'module_drawer': 'rounded',
        'color_mask': 'solid',
        'colors': {'front': (0, 0, 0), 'back': (255, 255, 255)}
    },
    'gapped': {
        'name': '间隙方形',
        'description': '模块之间有间隙',
        'module_drawer': 'gapped',
        'color_mask': 'solid',
        'colors': {'front': (0, 0, 0), 'back': (255, 255, 255)}
    },
    'circles': {
        'name': '圆点风格',
        'description': '圆形模块，现代感强',
        'module_drawer': 'circle',
        'color_mask': 'solid',
        'colors': {'front': (66, 133, 244), 'back': (255, 255, 255)}
    },
    'vertical_bars': {
        'name': '竖条风格',
        'description': '垂直条纹样式',
        'module_drawer': 'vertical_bars',
        'color_mask': 'solid',
        'colors': {'front': (0, 0, 0), 'back': (255, 255, 255)}
    },
    'horizontal_bars': {
        'name': '横条风格',
        'description': '水平条纹样式',
        'module_drawer': 'horizontal_bars',
        'color_mask': 'solid',
        'colors': {'front': (0, 0, 0), 'back': (255, 255, 255)}
    },
    'radial_gradient': {
        'name': '径向渐变',
        'description': '从中心向外的渐变效果',
        'module_drawer': 'square',
        'color_mask': 'radial_gradient',
        'colors': {
            'center': (66, 133, 244), 
            'front': (147, 51, 234), 
            'back': (255, 255, 255)
        }
    },
    'square_gradient': {
        'name': '方形渐变',
        'description': '方形渐变效果',
        'module_drawer': 'square',
        'color_mask': 'square_gradient',
        'colors': {
            'center': (52, 168, 83), 
            'front': (66, 133, 244), 
            'back': (255, 255, 255)
        }
    },
    'horizontal_gradient': {
        'name': '水平渐变',
        'description': '左右渐变效果',
        'module_drawer': 'rounded',
        'color_mask': 'horizontal_gradient',
        'colors': {
            'left': (66, 133, 244), 
            'right': (234, 67, 53), 
            'back': (255, 255, 255)
        }
    },
    'vertical_gradient': {
        'name': '垂直渐变',
        'description': '上下渐变效果',
        'module_drawer': 'rounded',
        'color_mask': 'vertical_gradient',
        'colors': {
            'top': (234, 67, 53), 
            'bottom': (66, 133, 244), 
            'back': (255, 255, 255)
        }
    },
    'blue_circles': {
        'name': '蓝色圆点',
        'description': '蓝色圆形模块',
        'module_drawer': 'circle',
        'color_mask': 'solid',
        'colors': {'front': (25, 118, 210), 'back': (255, 255, 255)}
    },
    'rounded_blue': {
        'name': '圆角蓝色',
        'description': '圆角模块，蓝色主题',
        'module_drawer': 'rounded',
        'color_mask': 'solid',
        'colors': {'front': (41, 98, 255), 'back': (255, 255, 255)}
    }
}

MODULE_DRAWERS = {
    'square': SquareModuleDrawer(),
    'gapped': GappedSquareModuleDrawer(),
    'circle': CircleModuleDrawer(),
    'rounded': RoundedModuleDrawer(),
    'vertical_bars': VerticalBarsDrawer(),
    'horizontal_bars': HorizontalBarsDrawer()
}


def get_available_styles() -> Dict[str, Dict[str, Any]]:
    return QR_STYLES


def generate_qr_code(
    data: str, 
    size: int = 10, 
    style: str = 'classic',
    custom_colors: Optional[Dict[str, Tuple[int, int, int]]] = None
) -> str:
    style_config = QR_STYLES.get(style, QR_STYLES['classic'])
    
    module_drawer = MODULE_DRAWERS.get(
        style_config['module_drawer'], 
        SquareModuleDrawer()
    )
    
    colors = custom_colors if custom_colors else style_config['colors']
    color_mask = _create_color_mask(style_config['color_mask'], colors)
    
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=size,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=module_drawer,
        color_mask=color_mask
    )
    
    img = img.convert('RGBA')
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def _create_color_mask(mask_type: str, colors: Dict[str, Tuple[int, int, int]]):
    back_color = colors.get('back', (255, 255, 255))
    
    if mask_type == 'solid':
        front_color = colors.get('front', (0, 0, 0))
        return SolidFillColorMask(back_color=back_color, front_color=front_color)
    
    elif mask_type == 'radial_gradient':
        center_color = colors.get('center', (0, 0, 0))
        front_color = colors.get('front', (0, 0, 0))
        return RadialGradiantColorMask(
            back_color=back_color,
            center_color=center_color,
            edge_color=front_color
        )
    
    elif mask_type == 'square_gradient':
        center_color = colors.get('center', (0, 0, 0))
        front_color = colors.get('front', (0, 0, 0))
        return SquareGradiantColorMask(
            back_color=back_color,
            center_color=center_color,
            edge_color=front_color
        )
    
    elif mask_type == 'horizontal_gradient':
        left_color = colors.get('left', (0, 0, 0))
        right_color = colors.get('right', (0, 0, 0))
        return HorizontalGradiantColorMask(
            back_color=back_color,
            left_color=left_color,
            right_color=right_color
        )
    
    elif mask_type == 'vertical_gradient':
        top_color = colors.get('top', (0, 0, 0))
        bottom_color = colors.get('bottom', (0, 0, 0))
        return VerticalGradiantColorMask(
            back_color=back_color,
            top_color=top_color,
            bottom_color=bottom_color
        )
    
    else:
        front_color = colors.get('front', (0, 0, 0))
        return SolidFillColorMask(back_color=back_color, front_color=front_color)

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
