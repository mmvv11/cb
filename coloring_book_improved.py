import base64
import os
import tempfile
from contextlib import contextmanager
from openai import OpenAI
from PIL import Image
from io import BytesIO
import cv2

# 지원하는 이미지 확장자
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif', '.gif', '.heic', '.heif'}


def resize_image(img, max_size=512):
    """이미지를 지정된 최대 크기로 리사이즈"""
    h, w = img.shape[:2]
    if max(h, w) <= max_size:
        return img
    
    if h > w:
        new_h = max_size
        new_w = int(w * max_size / h)
    else:
        new_w = max_size
        new_h = int(h * max_size / w)
    
    print(f"이미지 크기 조정: {w}x{h} → {new_w}x{new_h}")
    return cv2.resize(img, (new_w, new_h))


@contextmanager
def cv_image_to_temp_file(cv_image):
    """OpenCV 이미지를 임시 파일로 변환하는 컨텍스트 매니저"""
    _, buffer = cv2.imencode('.jpg', cv_image)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_file.write(buffer.tobytes())
    temp_file.close()
    
    file_obj = open(temp_file.name, 'rb')
    try:
        yield file_obj
    finally:
        file_obj.close()
        os.unlink(temp_file.name)


def validate_image_format(image_path):
    """이미지 포맷 검증"""
    try:
        ext = os.path.splitext(image_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS
    except Exception:
        return False


def load_image_universal(image_path):
    """다양한 포맷의 이미지를 OpenCV 형식으로 로드"""
    validate_image_format(image_path)
    
    # 한글 경로 문제 해결을 위해 PIL을 먼저 사용
    try:
        pil_img = Image.open(image_path)
        if pil_img.mode == 'RGBA':
            # 투명도가 있는 경우 흰 배경으로 합성
            background = Image.new('RGB', pil_img.size, (255, 255, 255))
            pil_img = Image.alpha_composite(background.convert('RGBA'), pil_img).convert('RGB')
        elif pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        
        # PIL을 OpenCV 형식으로 변환
        import numpy as np
        img_array = np.array(pil_img)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    except Exception as e:
        # 백업: OpenCV로 시도 (한글 경로에서는 실패할 수 있음)
        try:
            # 한글 경로 문제 해결을 위한 대안
            import numpy as np
            with open(image_path, 'rb') as f:
                file_bytes = np.frombuffer(f.read(), np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if img is not None:
                    return img
        except:
            pass
        
        raise ValueError(f"이미지를 불러올 수 없습니다: {image_path}. 오류: {e}")


def process_image_for_api(image_path, max_size=512):
    """이미지를 로드하고 API용으로 처리"""
    img = load_image_universal(image_path)
    resized = resize_image(img, max_size)
    return cv_image_to_temp_file(resized)


def convert_to_coloring_book(image_path, output_path=None, max_size=512):
    """이미지를 컬러링북 스타일로 변환"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수를 설정해주세요")
    
    client = OpenAI(api_key=api_key)
    
    prompt = """convert this image into a coloring book style image with clear outlines and no shading.
Make sure the outlines are bold and distinct, suitable for coloring."""
    
    with process_image_for_api(image_path, max_size) as temp_img:
        result = client.images.edit(
            model="gpt-image-1",
            image=temp_img,
            prompt=prompt,
            size="1024x1536"
        )
    
    # 결과 이미지 저장
    if output_path is None:
        file_name = os.path.splitext(image_path)[0]
        output_path = f"{file_name}_converted.jpg"
    
    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_bytes))
    image.save(output_path, format="JPEG", quality=80, optimize=True)
    
    print(f"컬러링북 이미지 저장: {output_path}")
    return output_path


if __name__ == "__main__":
    # 사용 예시
    input_image = "bom.jpg"
    
    try:
        output_file = convert_to_coloring_book(input_image)
        print(f"변환 완료: {output_file}")
    except Exception as e:
        print(f"오류 발생: {e}")