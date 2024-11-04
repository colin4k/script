import streamlit as st
import subprocess
import os
import sys
import threading
import queue
import yaml
from pathlib import Path
import warnings
from warnings import filterwarnings

# 忽略特定的警告信息
filterwarnings('ignore', category=UserWarning, message='torchaudio._backend.set_audio_backend.*')

# 设置上传文件大小限制为1GB
st.set_page_config(
    page_title="WhisperX 音视频转文字工具",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 修改上传文件大小限制
st.markdown("""
    <style>
        [data-testid="stFileUploader"] {
            width: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# 在启动时设置环境变量
if not os.environ.get("STREAMLIT_SERVER_MAX_UPLOAD_SIZE"):
    os.environ["STREAMLIT_SERVER_MAX_UPLOAD_SIZE"] = "1024"  # 设置为1GB

# 添加版本检查和错误处理
try:
    import google.protobuf
except ImportError:
    st.error("缺少必要的依赖，请运行: pip install protobuf==5.28.3")
    sys.exit(1)

# 添加队列输出函数
def enqueue_output(out, queue):
    for line in iter(out.readline, ''):
        queue.put(line)
    out.close()

# 添加登录验证函数
def load_users():
    settings_path = Path("settings.yaml")
    if not settings_path.exists():
        st.error("找不到 settings.yaml 配置文件")
        return {}
    
    with open(settings_path) as f:
        settings = yaml.safe_load(f)
    return {user['username']: user['password'] for user in settings.get('users', [])}

def check_login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("登录")
        users = load_users()
        
        if not users:
            return False
            
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        
        if st.button("登录"):
            if username in users and users[username] == password:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("用户名或密码错误")
        return False
    return True

# 添加登录检查
if not check_login():
    st.stop()

st.title("WhisperX 音视频转文字工具")

# 文件上传
uploaded_file = st.file_uploader("上传音视频文件", type=['mp4', 'mp3', 'wav', 'mkv'])

# 获temp目录中的第一个音视频文件
def get_first_media_file():
    if os.path.exists("temp"):
        valid_extensions = ('.mp4', '.mp3', '.wav', '.mkv')
        for file in os.listdir("temp"):
            if file.lower().endswith(valid_extensions):
                return os.path.join("temp", file)
    return None

# 参数设置
with st.expander("参数设置", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        batch_size = st.number_input("Batch Size", value=4, min_value=2)
        model = st.text_input("模型", value="Huan69/Belle-whisper-large-v3-zh-punct-fasterwhisper")
        device = st.selectbox("设备", ["cuda", "cpu"])
        compute_type = st.selectbox("计算类型", ["float16", "int8", "float32"])
        
    with col2:
        language = st.text_input("语言", value="zh")
        hf_token = st.text_input("Hugging Face Token", value="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")
        threads = st.number_input("线程数", value=8, min_value=1)
        initial_prompt = st.text_area("初始提示词", value="生于忧患，死于欢乐。不亦快哉?")

    diarize = st.checkbox("启用说话人分离", value=True)
    highlight_words = st.checkbox("高亮显示单词", value=True)
    print_progress = st.checkbox("显示进度", value=True)

# 在参数设置部分之后添加按钮
col1, col2 = st.columns([1, 4])  # 创建两个不同宽度的列
delete_button = col1.button("删除文件")
start_button = col2.button("开始转换")

# 添加删除功能
if delete_button:
    try:
        # 清理临时文件夹
        if os.path.exists("temp"):
            for file in os.listdir("temp"):
                os.remove(os.path.join("temp", file))
        
        # 清理输出文件夹
        if os.path.exists("output"):
            for file in os.listdir("output"):
                os.remove(os.path.join("output", file))
        
        # 清理会话状态
        if 'txt_content' in st.session_state:
            del st.session_state.txt_content
        if 'srt_content' in st.session_state:
            del st.session_state.srt_content
            
        st.success("所有文件已清理完成！")
    except Exception as e:
        st.error(f"清理文件时发生错误: {str(e)}")

# 修改开始转换的条件判断
if start_button:
    if uploaded_file is not None:
        # 处理新上传的文件，但不删除已有文件
        try:
            os.makedirs("temp", exist_ok=True)
            temp_file_path = os.path.join("temp", uploaded_file.name)
            with open(temp_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        except Exception as e:
            st.error(f"保存文件时发生错误: {str(e)}")
            
    # 检查是否存在可处理的文件
    temp_file_path = get_first_media_file()
    if temp_file_path is None:
        st.warning("没有找到可处理的文件，请先上传！")
    else:
        try:
            # 生成输出文件名
            base_name = os.path.splitext(os.path.basename(temp_file_path))[0]
            output_txt = os.path.join("output", f"{base_name}.txt")
            output_srt = os.path.join("output", f"{base_name}.srt")
            
            # 创建输出目录
            os.makedirs("output", exist_ok=True)
            
            # 添加输出文件参数
            command = [
                "whisperx",
                temp_file_path,
                "--output_dir", "output",
                "--batch_size", str(batch_size),
                "--model", model,
                "--device", device,
                "--compute_type", compute_type,
                "--language", language,
                "--hf_token", hf_token,
                "--threads", str(threads)
            ]
            
            # 修改可选参数的添加方式
            if initial_prompt:
                command.extend(["--initial_prompt", initial_prompt])
            if diarize:
                command.append("--diarize")
            if highlight_words:
                command.extend(["--highlight_words", "True"])
            if print_progress:
                command.extend(["--print_progress", "True"])
            
            st.info("转换进行中...")
            # 修改进程创建和输出处理部分
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # 创建输出容器
            output_container = st.empty()
            output_text = ""
            
            # 修改实时读取输出的部分
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()
            stdout_thread = threading.Thread(target=enqueue_output, args=(process.stdout, stdout_queue))
            stderr_thread = threading.Thread(target=enqueue_output, args=(process.stderr, stderr_queue))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()

            # 添加一个计数器用于生成唯一的key
            update_counter = 0
            jj=1
            # 使用非阻塞方式读取输出
            while process.poll() is None:
                try:
                    # 读取标准输出和标准错误
                    try:
                        while True:
                            try:
                                output = stdout_queue.get_nowait()
                                print(output.strip())  # 打印到控制台
                                output_text += output
                            except queue.Empty:
                                break

                        while True:
                            try:
                                error = stderr_queue.get_nowait()
                                print(error.strip(), file=sys.stderr)  # 打印错误到控制台
                                output_text += f"错误: {error}"
                            except queue.Empty:
                                break

                        # 使用递增的计数器作为唯一key
                        update_counter += 1
                        jj+=1
                        output_container.text_area(
                            "实时输出", 
                            output_text, 
                            height=300, 
                            key=f"output_area_{update_counter}"
                        )
                        
                    except queue.Empty:
                        pass

                    st.session_state.current_output = output_text
                except Exception as e:
                    st.error(f"读取输出时发生错误: {str(e)}")
                    break

            # 获取最终的返回码
            return_code = process.poll()
            
            if return_code == 0:
                st.success("转换完成！")
                # 使用会话状态来保存文件内容
                if 'txt_content' not in st.session_state and os.path.exists(output_txt):
                    with open(output_txt, 'r', encoding='utf-8') as f:
                        st.session_state.txt_content = f.read()
                
                if 'srt_content' not in st.session_state and os.path.exists(output_srt):
                    with open(output_srt, 'r', encoding='utf-8') as f:
                        st.session_state.srt_content = f.read()
                
                # 添加下载按钮
                col1, col2 = st.columns(2)
                
                # 使用会话状态中的内容显示下载按钮
                if hasattr(st.session_state, 'txt_content'):
                    col1.download_button(
                        label="下载TXT文件",
                        data=st.session_state.txt_content,
                        file_name=f"{base_name}.txt",
                        mime="text/plain"
                    )
                
                if hasattr(st.session_state, 'srt_content'):
                    col2.download_button(
                        label="下载SRT字幕文件",
                        data=st.session_state.srt_content,
                        file_name=f"{base_name}.srt",
                        mime="text/plain"
                    )
            else:
                st.error("转换失败")
                # 修改这里：使用之前收集的错误输出而不是未定义的stderr
                st.error(output_text)  # 使用之前收集的所有输出，包括错误信息
                
        except Exception as e:
            st.error(f"发生错误: {str(e)}")
            st.error("请确保已正确安装所有依赖：\n1. pip install protobuf==5.28.3\n2. pip install whisperx\n3. pip install -U streamlit")
        finally:
            # 移除清理临时文件的代码
            pass
            # 不再执行：
            # if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            #     os.remove(temp_file_path)

else:
    if start_button and uploaded_file is None:
        st.warning("请先上传文件！")

st.markdown("""
### 使用说明
1. 上传需要转换的音视频文件
2. 根据需要调整参数设置
3. 点击"开始转换"按钮
4. 等待转换完成后查看结果
""")