import streamlit as st
import tempfile
import os
from PIL import Image
from coloring_book_improved import convert_to_coloring_book, validate_image_format
import logging

# 로깅 설정 (프로덕션에서는 WARNING 이상만)
logging.basicConfig(
    level=logging.WARNING,  # INFO 로그 숨김
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),  # 파일로만 로그 저장
        # logging.StreamHandler()  # 콘솔 출력 비활성화
    ]
)
logger = logging.getLogger(__name__)

# 페이지 설정
st.set_page_config(
    page_title="컬러링북 변환기",
    page_icon="🎨",
    initial_sidebar_state="collapsed"  # 사이드바 숨김
)

# 제목
st.title("🎨 컬러링북 변환기")
st.markdown("이미지를 업로드하면 컬러링북으로 변환해드립니다!")

# 사용법 및 지원 형식
with st.expander("📝 사용법 및 지원 형식", expanded=True):
    col_help1, col_help2 = st.columns(2)
    with col_help1:
        st.markdown("""
        **사용법**
        1. 이미지 파일 업로드
        2. 🔄 버튼으로 회전 (필요시)
        3. 테마 선택
        4. 변환하기 클릭
        5. 결과 다운로드
        """)
    with col_help2:
        st.markdown("""
        **지원 형식**
        - 파일 형식: PNG, JPG, JPEG
        - 최대 크기: 10MB
        - 권장 해상도: 1000x1000px 이하
        """)

# 변환 설정 영역
st.markdown("### ⚙️ 변환 설정")
col_theme1, col_theme2, col_theme3 = st.columns([1, 1, 2])

with col_theme1:
    # 테마 선택
    theme_options = ["기본", "귀엽게", "시원하게", "따뜻하게", "직접입력"]
    selected_theme = st.selectbox("테마 선택", theme_options)

with col_theme2:
    if selected_theme == "직접입력":
        custom_theme = st.text_input("테마 키워드 입력", placeholder="예: 몽환적으로")
        theme = custom_theme if custom_theme else "기본"
    else:
        theme = selected_theme
        st.write("")  # 빈 공간

with col_theme3:
    if selected_theme != "직접입력":
        st.info(f"선택된 테마: {theme}")
    else:
        st.write("")  # 빈 공간

st.markdown("---")

# 메인 영역
main_container = st.container()
with main_container:
    col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📷 원본 이미지")
    
    # 파일 업로더
    uploaded_file = st.file_uploader(
        "이미지를 선택하세요",
        type=['png', 'jpg', 'jpeg'],
        help="PNG, JPG, JPEG 파일만 지원됩니다 (최대 10MB)"
    )
    
    if uploaded_file is not None:
        # 파일 크기 체크
        if uploaded_file.size > 10 * 1024 * 1024:  # 10MB
            st.error("파일 크기가 10MB를 초과합니다.")
            st.stop()
        
        # 이미지 표시
        try:
            # 세션 상태에 이미지와 회전 각도 저장
            if 'original_image' not in st.session_state or st.session_state.get('uploaded_file_name') != uploaded_file.name:
                # 파일 포인터를 처음으로 되돌리기
                uploaded_file.seek(0)
                st.session_state.original_image = Image.open(uploaded_file)
                st.session_state.rotation_angle = 0
                st.session_state.uploaded_file_name = uploaded_file.name
            
            # 회전된 이미지 생성
            if st.session_state.rotation_angle != 0:
                rotated_image = st.session_state.original_image.rotate(
                    -st.session_state.rotation_angle,  # PIL은 시계 반대방향이 양수
                    expand=True  # 이미지 크기 자동 조정
                )
            else:
                rotated_image = st.session_state.original_image
            
            # 이미지와 회전 버튼을 오버랩으로 표시
            image_container = st.container()
            with image_container:
                st.image(rotated_image, caption=f"업로드된 파일: {uploaded_file.name}")
                
                # 회전 버튼을 이미지 위에 오버랩
                st.markdown("""
                <style>
                .rotate-button {
                    position: relative;
                    top: -60px;
                    right: 10px;
                    float: right;
                    z-index: 999;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # 회전 버튼
                if st.button("🔄 90도 회전", help="90도 회전", key="rotate_btn"):
                    st.session_state.rotation_angle = (st.session_state.rotation_angle + 90) % 360
                    st.rerun()
            
            # 이미지 정보
            st.info(f"크기: {rotated_image.size[0]} x {rotated_image.size[1]} 픽셀")
            
            # 변환에 사용할 이미지를 세션에 저장
            st.session_state.current_image = rotated_image
            
        except Exception as e:
            logger.error(f"이미지 읽기 실패: {str(e)}")
            st.error("이미지를 읽을 수 없습니다. 올바른 이미지 파일인지 확인해주세요.")
            st.stop()

with col2:
    st.subheader("🎨 변환 결과")
    
    if uploaded_file is not None:
        # 변환 버튼
        if st.button("🚀 변환하기", type="primary", use_container_width=True):
            try:
                # 프로그래스 바와 상태 메시지
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("이미지 검증 중...")
                progress_bar.progress(20)
                
                # 회전된 이미지를 임시 파일로 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    # 현재 표시된 이미지(회전 적용된) 사용
                    current_image = st.session_state.get('current_image', st.session_state.original_image)
                    
                    # RGBA 모드(투명도 포함)를 RGB로 변환
                    if current_image.mode in ('RGBA', 'LA', 'P'):
                        # 흰색 배경으로 변환
                        rgb_image = Image.new('RGB', current_image.size, (255, 255, 255))
                        if current_image.mode == 'P':
                            current_image = current_image.convert('RGBA')
                        rgb_image.paste(current_image, mask=current_image.split()[-1] if current_image.mode == 'RGBA' else None)
                        current_image = rgb_image
                    
                    current_image.save(tmp_file.name, 'JPEG', quality=95)
                    tmp_path = tmp_file.name
                
                status_text.text("이미지 형식 검증 중...")
                progress_bar.progress(40)
                
                # 이미지 형식 검증
                try:
                    if not validate_image_format(tmp_path):
                        st.error("지원하지 않는 이미지 형식입니다.")
                        os.unlink(tmp_path)
                        st.stop()
                except Exception as e:
                    logger.error(f"이미지 검증 실패: {str(e)}")
                    st.error("이미지 검증에 실패했습니다. 다른 이미지를 시도해주세요.")
                    os.unlink(tmp_path)
                    st.stop()
                
                status_text.text("컬러링북으로 변환 중...")
                progress_bar.progress(60)
                
                # 변환 실행
                result_path = convert_to_coloring_book(tmp_path, theme)
                
                progress_bar.progress(90)
                status_text.text("변환 완료!")
                
                # 결과 이미지 표시
                if result_path and os.path.exists(result_path):
                    result_image = Image.open(result_path)
                    st.image(result_image, caption="변환된 컬러링북")
                    
                    progress_bar.progress(100)
                    status_text.text("✅ 변환이 완료되었습니다!")
                    
                    # 다운로드 버튼
                    with open(result_path, "rb") as file:
                        st.download_button(
                            label="📥 컬러링북 다운로드",
                            data=file.read(),
                            file_name=f"coloring_book_{uploaded_file.name}",
                            mime="image/png",
                            use_container_width=True
                        )
                    
                    # 임시 파일 정리
                    try:
                        os.unlink(tmp_path)
                        os.unlink(result_path)
                    except:
                        pass
                        
                else:
                    st.error("변환에 실패했습니다. 다시 시도해주세요.")
                    
            except Exception as e:
                logger.error(f"변환 중 오류 발생: {str(e)}")
                st.error("변환 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
                
                # 임시 파일 정리
                try:
                    if 'tmp_path' in locals():
                        os.unlink(tmp_path)
                except:
                    pass
    else:
        st.info("👈 왼쪽에서 이미지를 업로드해주세요")

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🎨 컬러링북 변환기 | wjdwldns0905@gmail.com</p>
    </div>
    """, 
    unsafe_allow_html=True
)