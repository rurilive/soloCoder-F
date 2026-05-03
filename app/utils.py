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


def generate_qr_with_logo(
    data: str,
    logo_image: Image.Image,
    size: int = 10,
    style: str = 'classic',
    logo_size_ratio: float = 0.25,
    logo_round: bool = True,
    logo_border: bool = True,
    logo_border_color: Tuple[int, int, int] = (255, 255, 255),
    logo_border_width: int = 4
) -> str:
    qr_base64 = generate_qr_code(data, size, style)
    qr_img_data = base64.b64decode(qr_base64.split(',')[1])
    qr_img = Image.open(io.BytesIO(qr_img_data)).convert('RGBA')
    
    qr_width, qr_height = qr_img.size
    logo_max_size = int(min(qr_width, qr_height) * logo_size_ratio)
    
    logo_img = logo_image.convert('RGBA')
    
    logo_ratio = logo_img.width / logo_img.height
    if logo_ratio > 1:
        logo_new_width = logo_max_size
        logo_new_height = int(logo_max_size / logo_ratio)
    else:
        logo_new_height = logo_max_size
        logo_new_width = int(logo_max_size * logo_ratio)
    
    logo_img = logo_img.resize((logo_new_width, logo_new_height), Image.Resampling.LANCZOS)
    
    if logo_round:
        mask = Image.new('L', (logo_new_width, logo_new_height), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, logo_new_width, logo_new_height), fill=255)
        
        logo_rounded = Image.new('RGBA', (logo_new_width, logo_new_height), (0, 0, 0, 0))
        logo_rounded.paste(logo_img, (0, 0), mask=mask)
        logo_img = logo_rounded
    
    if logo_border:
        border_size = logo_border_width
        bordered_width = logo_new_width + 2 * border_size
        bordered_height = logo_new_height + 2 * border_size
        
        bordered_logo = Image.new('RGBA', (bordered_width, bordered_height), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(bordered_logo)
        
        if logo_round:
            border_draw.ellipse((0, 0, bordered_width, bordered_height), fill=logo_border_color)
        else:
            rect_radius = min(bordered_width, bordered_height) // 8
            border_draw.rounded_rectangle((0, 0, bordered_width, bordered_height), rect_radius, fill=logo_border_color)
        
        paste_x = border_size
        paste_y = border_size
        bordered_logo.paste(logo_img, (paste_x, paste_y), mask=logo_img)
        
        logo_img = bordered_logo
        logo_new_width = bordered_width
        logo_new_height = bordered_height
    
    paste_x = (qr_width - logo_new_width) // 2
    paste_y = (qr_height - logo_new_height) // 2
    
    qr_img.paste(logo_img, (paste_x, paste_y), mask=logo_img)
    
    buffered = io.BytesIO()
    qr_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def generate_qr_on_background(
    data: str,
    background_image: Image.Image,
    size: int = 10,
    style: str = 'classic',
    qr_position: str = 'center',
    qr_size_ratio: float = 0.6,
    qr_opacity: float = 1.0,
    qr_padding: int = 20,
    qr_background: Optional[Tuple[int, int, int, int]] = (255, 255, 255, 200)
) -> str:
    bg_img = background_image.convert('RGBA')
    bg_width, bg_height = bg_img.size
    
    qr_base64 = generate_qr_code(data, size, style)
    qr_img_data = base64.b64decode(qr_base64.split(',')[1])
    qr_img = Image.open(io.BytesIO(qr_img_data)).convert('RGBA')
    
    min_bg_dim = min(bg_width, bg_height)
    qr_target_size = int(min_bg_dim * qr_size_ratio)
    
    qr_ratio = qr_img.width / qr_img.height
    if qr_ratio > 1:
        qr_new_width = qr_target_size
        qr_new_height = int(qr_target_size / qr_ratio)
    else:
        qr_new_height = qr_target_size
        qr_new_width = int(qr_target_size * qr_ratio)
    
    qr_img = qr_img.resize((qr_new_width, qr_new_height), Image.Resampling.LANCZOS)
    
    if qr_opacity < 1.0:
        alpha = qr_img.split()[3]
        alpha = alpha.point(lambda p: int(p * qr_opacity))
        qr_img.putalpha(alpha)
    
    if qr_background:
        qr_with_bg = Image.new('RGBA', (qr_new_width + 2 * qr_padding, qr_new_height + 2 * qr_padding), qr_background)
        qr_with_bg.paste(qr_img, (qr_padding, qr_padding), mask=qr_img)
        qr_img = qr_with_bg
        qr_new_width += 2 * qr_padding
        qr_new_height += 2 * qr_padding
    
    if qr_position == 'center':
        paste_x = (bg_width - qr_new_width) // 2
        paste_y = (bg_height - qr_new_height) // 2
    elif qr_position == 'top_left':
        paste_x = 20
        paste_y = 20
    elif qr_position == 'top_right':
        paste_x = bg_width - qr_new_width - 20
        paste_y = 20
    elif qr_position == 'bottom_left':
        paste_x = 20
        paste_y = bg_height - qr_new_height - 20
    elif qr_position == 'bottom_right':
        paste_x = bg_width - qr_new_width - 20
        paste_y = bg_height - qr_new_height - 20
    else:
        paste_x = (bg_width - qr_new_width) // 2
        paste_y = (bg_height - qr_new_height) // 2
    
    bg_img.paste(qr_img, (paste_x, paste_y), mask=qr_img)
    
    buffered = io.BytesIO()
    bg_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def generate_artistic_qr(
    data: str,
    art_image: Image.Image,
    size: int = 10,
    style: str = 'classic',
    blend_mode: str = 'overlay',
    qr_opacity: float = 0.7,
    art_opacity: float = 0.3,
    qr_color_override: Optional[Tuple[int, int, int]] = None
) -> str:
    qr_base64 = generate_qr_code(data, size, style)
    qr_img_data = base64.b64decode(qr_base64.split(',')[1])
    qr_img = Image.open(io.BytesIO(qr_img_data)).convert('RGBA')
    
    art_img = art_image.convert('RGBA')
    art_img = art_img.resize(qr_img.size, Image.Resampling.LANCZOS)
    
    if qr_color_override:
        qr_data = qr_img.load()
        for y in range(qr_img.height):
            for x in range(qr_img.width):
                r, g, b, a = qr_data[x, y]
                if r < 128 and g < 128 and b < 128:
                    qr_data[x, y] = (*qr_color_override, a)
    
    if blend_mode == 'overlay':
        result = Image.blend(art_img, qr_img, qr_opacity)
    elif blend_mode == 'multiply':
        result = Image.new('RGBA', qr_img.size)
        qr_pixels = qr_img.load()
        art_pixels = art_img.load()
        result_pixels = result.load()
        
        for y in range(qr_img.height):
            for x in range(qr_img.width):
                qr_r, qr_g, qr_b, qr_a = qr_pixels[x, y]
                art_r, art_g, art_b, art_a = art_pixels[x, y]
                
                if qr_r < 128 and qr_g < 128 and qr_b < 128:
                    result_pixels[x, y] = (
                        int(art_r * art_opacity),
                        int(art_g * art_opacity),
                        int(art_b * art_opacity),
                        255
                    )
                else:
                    result_pixels[x, y] = (255, 255, 255, 255)
    elif blend_mode == 'colorize':
        result = Image.new('RGBA', qr_img.size)
        qr_pixels = qr_img.load()
        art_pixels = art_img.load()
        result_pixels = result.load()
        
        for y in range(qr_img.height):
            for x in range(qr_img.width):
                qr_r, qr_g, qr_b, qr_a = qr_pixels[x, y]
                art_r, art_g, art_b, art_a = art_pixels[x, y]
                
                if qr_r < 128 and qr_g < 128 and qr_b < 128:
                    result_pixels[x, y] = (art_r, art_g, art_b, 255)
                else:
                    result_pixels[x, y] = (255, 255, 255, 255)
    elif blend_mode == 'silhouette':
        result = art_img.copy()
        qr_pixels = qr_img.load()
        result_pixels = result.load()
        
        for y in range(qr_img.height):
            for x in range(qr_img.width):
                qr_r, qr_g, qr_b, qr_a = qr_pixels[x, y]
                if qr_r > 200 and qr_g > 200 and qr_b > 200:
                    result_pixels[x, y] = (255, 255, 255, 255)
    else:
        result = Image.blend(art_img, qr_img, qr_opacity)
    
    buffered = io.BytesIO()
    result.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def image_to_base64(img: Image.Image) -> str:
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def base64_to_image(base64_str: str) -> Image.Image:
    if ',' in base64_str:
        base64_str = base64_str.split(',')[1]
    img_data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(img_data))
