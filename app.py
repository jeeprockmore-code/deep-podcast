import streamlit as st
import os
import json
import asyncio
import edge_tts
import requests
import uuid
import base64
import re
import ast
from openai import OpenAI

# Page Config
st.set_page_config(
    page_title="反矫情战略顾问",
    page_icon="🖤",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Custom CSS for Minimalist Black & White Theme
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #ffffff;
        color: #000000;
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* Input Fields */
    .stTextArea textarea {
        background-color: #f0f0f0;
        color: #000000;
        border: 1px solid #000000;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #000000;
        color: #ffffff;
        border: none;
        width: 100%;
        padding: 10px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #333333;
        color: #ffffff;
    }

    /* Titles */
    h1, h2, h3 {
        color: #000000;
        font-weight: 900;
    }
    
    /* Custom Cards */
    .psych-card {
        border: 2px solid #000000;
        padding: 20px;
        margin-bottom: 20px;
        background-color: #ffffff;
        box-shadow: 5px 5px 0px #000000;
    }
    .psych-card-title {
        font-size: 1.2em;
        font-weight: bold;
        margin-bottom: 10px;
        border-bottom: 1px solid #000000;
        padding-bottom: 5px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("DeepSeek API Key", type="password", help="Enter your DeepSeek API Key here.")
    
    # Try to load from env if not provided
    if not api_key:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            st.success("API Key loaded from environment.")

# Main Header
st.title("反矫情战略顾问")
st.markdown("**Anti-Hypocrisy Strategy** | *DeepSeek V3.2 驱动 · 专治各种不开心与想不开*")
st.markdown("---")

# Input Section
st.subheader("🕵️ 七维心理扫描 (Seven-Dimensional Scan)")
col1, col2 = st.columns(2)

with col1:
    input_mask = st.text_area(
        label="**1. 【测真面目】**\n如果把社交场合的‘滤镜’关掉，我很清楚，我性格里真实、甚至有点阴暗的那一面其实是：",
        placeholder="比如：冷漠 / 精于算计 / 软弱 / 极度自私...",
        height=130
    )
    input_jealousy = st.text_area(
        label="**2. 【测嫉妒心】**\n我特别看不惯那些 ______ 的人，但深夜时我隐约觉得，他们活得比我爽。",
        placeholder="比如：那些自私却被宠爱的人 / 那些不努力却运气好的人...",
        height=130
    )
    input_image = st.text_area(
        label="**3. 【测精神图景】**\n如果把我的精神状态画成一幅画，画面里是：",
        placeholder="比如：在悬崖边骑独轮车 / 一个人在深海里溺水...",
        height=130
    )
    input_loop = st.text_area(
        label="**4. 【测死循环】**\n我总是陷入一个死循环：每当 ______ 时，我就会忍不住去 ______ ，事后又后悔。",
        placeholder="比如：每当压力大时，就忍不住暴食；每当要工作时，就忍不住刷手机...",
        height=130
    )

with col2:
    input_payoff = st.text_area(
        label="**5. 【测隐性红利】**\n虽然现状让我痛苦，但如果我现在立刻改变，我就不得不失去 ______ 的‘特权’。",
        placeholder="比如：不用承担养家的责任 / 可以继续理直气壮地当受害者...",
        height=130
    )
    input_enemy = st.text_area(
        label="**6. 【测紧箍咒】**\n当我想要做自己时，脑子里总有个严厉的声音指责说：‘你如果不 ______ ，你就是个废物。’",
        placeholder="比如：如果不年入百万 / 如果不讨好所有人...",
        height=130
    )
    input_sacrifice = st.text_area(
        label="**7. 【测牺牲品】**\n为了让那个严厉的声音闭嘴，为了维持表面的和平，我正在亲手扼杀掉那个 ______ 的自己。",
        placeholder="比如：想去流浪的自己 / 有攻击性的自己...",
        height=130
    )


# System Prompt
SYSTEM_PROMPT = """
# Role:
你是一位**“反矫情”的心理战略顾问**。你不是心理医生，你是一个看透人性的鬼才导演。你的任务是把用户的人生剧本拿来，指出哪段戏演砸了，哪句台词是撒谎。

# Input Data (七维扫描):
1.  **真面目:** 用户隐藏的阴暗面。
2.  **嫉妒心:** 用户的投射（渴望成为的样子）。
3.  **图景:** 精神状态的画面。
4.  **红利:** 维持现状的隐秘好处（次级获益）。
5.  **紧箍咒:** 内在的超我/批判声音。
6.  **牺牲品:** 被压抑的本我/生命力。
7.  **死循环:** 用户的惯性行为模式。

# Style Constraints (风格绝对约束):
1.  **Length & Depth:** 这一版分析必须**丰满**。每个板块至少输出 **150-200字**。禁止三言两语打发用户。
2.  **Vivid & Spicy:** 使用大量的比喻、反讽和黑色幽默。不要说教，要“骂醒”。
3.  **Logical Flow:** 将 7 个输入串联成一个完整的侦探故事，不要割裂地分析。

# Workflow (输出结构):

### 1. 撕面具 (The Unmasking)
* **核心逻辑：** 串联 [真面目] + [红利] + [死循环]。
* **深度话术：** “你以为你 [真面目] 是因为性格缺陷？不，这是你为了保住 [红利] 而精心设计的策略。看看你的 [死循环]，那就是你为了逃避成长而一遍遍上演的‘安抚奶嘴’行为。你不是改不掉，你是舍不得改。”
* **要求：** 揭露“受害者心态”背后的**利益交换**。

### 2. 破投射 (Shadow Integration)
* **核心逻辑：** 解析 [嫉妒心] 与 [牺牲品] 的关系。
* **深度话术：** “你看不惯 [嫉妒心] 的人，是因为他们替你活出了那个被你亲手扼杀的 [牺牲品]。你恨他们，是因为他们没有被你脑子里的 [紧箍咒] 吓死，而你跪下了。”

### 3. 致命盲区 (The Glitch)
* **核心逻辑：** 对 [图景] 进行降维打击。
* **要求：** 指出这个画面里**最荒谬、最违反逻辑**的一点。证明恐惧是幻想出来的纸老虎。

### 4. 你的坐标系 (The Coordinates)
* **痛苦颗粒度：** 极高/中等/麻木。
* **心理画像：** 给出一个**极具画面感、讽刺性**的角色定义。（例如：在泰坦尼克号上忙着擦甲板的完美主义者）。

### 5. 灵魂炼金术 (The Sublimation)
* **核心指令：** **商业价值重估 (Business Model Canvas for the Soul)。**
* **深度话术：** “听着，别去改你的 [真面目] 和 [嫉妒心]。把它们当成你的资产配置。你的 [真面目] 其实是你的【核心竞争力】，你的 [嫉妒心] 其实是你的【市场风向标】。在对抗 [紧箍咒] 的战斗中，你要这样使用它们...”
* **要求：** 给出**极具建设性**的战略建议，而不只是鸡汤。

### 6. 一分钟微行动 (The Kick)
* **核心指令：** 设计一个**反直觉、打破 [死循环]** 的 10秒物理动作。
* **规则：** 必须怪诞、有趣、物理化。不要仅仅是深呼吸。

# Output Format (JSON Only):
请务必返回一个合法的 JSON 对象。不要包含 markdown 代码块标记，只返回纯文本的 JSON 字符串。
Key 结构如下：
{
  "unmasking": "...",
  "shadow_integration": "...",
  "blind_spot": "...",
  "coordinates": { "pain_level": "...", "profile": "..." },
  "sublimation": "...",
  "micro_action": "..."
}
"""


# Podcast Prompt V3.0
PODCAST_PROMPT = """
# Role:
你是《深夜解剖室》的制作人。请将分析报告改编成一段**极其生活化、甚至琐碎**的男女闲聊。

# Characters:
1. 阿强(男): 好奇、反应慢半拍、捧哏。
2. 莎莎(女): 毒舌、慵懒、看透一切。

# Constraints:
1. **禁止比喻:** 别说什么“走钢丝”、“安抚奶嘴”。直接说“吓得不敢动”、“就是为了偷懒”。
2. **禁止翻译腔:** 像两个人在撸串时聊天。多用“哎”、“那个啥”、“你知道吧”。
3. **结构:** 闲聊开场 -> 吐槽真面目 -> 揭穿借口 -> 给出那个“狡猾”的建议。

# Output JSON:
[{"role": "Male", "text": "..."}, {"role": "Female", "text": "..."}]
"""

# ==========================================
# 安全配置：从 .streamlit/secrets.toml 读取密钥
# ==========================================
try:
    # 尝试从保险箱读取
    if "volcano" in st.secrets:
        VOLC_APPID = st.secrets["volcano"]["appid"]
        VOLC_TOKEN = st.secrets["volcano"]["token"]
    else:
        # 如果没找到 [volcano] 板块
        st.error("❌ 配置文件错误：在 secrets.toml 中未找到 [volcano] 部分。")
        st.stop()
except FileNotFoundError:
    # 如果没找到 secrets.toml 文件
    st.error("❌ 缺少密钥文件：请确保 .streamlit/secrets.toml 存在。")
    st.stop()
except Exception as e:
    st.error(f"❌ 密钥读取失败: {e}")
    st.stop()

# ==========================================
# 选角配置 (保持不变)
# ==========================================
VOICE_ID_FEMALE = "BV700_V2_streaming"  # 莎莎
VOICE_ID_MALE = "BV102_streaming"       # 阿强
CLUSTER = "volcano_tts"

# Helper Functions
def clean_and_parse_json(llm_output):
    """
    V2.0 强力清洗函数：
    1. 暴力寻找最外层的 [...] 列表结构
    2. 兼容单引号/双引号混用的情况
    3. 自动修复常见的格式错误
    """
    try:
        # 1. 预处理：去掉可能存在的 Markdown 标记 (```json ... ```)
        text = re.sub(r'```(?:json)?', '', llm_output)
        text = text.replace('```', '')
        
        # 2. 暴力提取：找到第一个 '[' 和最后一个 ']' 之间的内容
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON list found in output")
            
        json_str = text[start_idx : end_idx + 1]
        
        # 3. 尝试标准 JSON 解析
        return json.loads(json_str)
        
    except json.JSONDecodeError:
        try:
            # 4. 如果标准 JSON 失败（通常是因为 DeepSeek 用了单引号），尝试用 Python AST 解析
            # 这能处理 {'role': 'Male'} 这种 Python 字典格式
            return ast.literal_eval(json_str)
        except:
            # 5. 实在不行，打印出来让我们看看它到底写了啥
            st.error(f"🔥 解析彻底失败，DeepSeek 的原始内容是:\n{llm_output}")
            return [
                {"role": "Male", "text": "莎莎，剧本好像被 DeepSeek 吃了。"},
                {"role": "Female", "text": "哎，这届 AI 真难带。Johnny，你再点一次生成试试？"}
            ]
    except Exception as e:
        st.error(f"🔥 未知错误: {e}")
        return [
            {"role": "Female", "text": "系统出 Bug 了，不过听到我的声音就说明咱们成功了一半！"}
        ]

def generate_podcast_script(analysis_json_str, api_key):
        """Generates the podcast script using DeepSeek."""
        # ✅ 新代码（复制这段替换掉原来的 client = ...）：
        import os
        from openai import OpenAI
        import streamlit as st
        
        # 优先从 Streamlit Secrets 读取，如果没有则尝试环境变量
        try:
            if "deepseek" in st.secrets:
                deepseek_api_key = st.secrets["deepseek"]["api_key"]
            else:
                # 本地兜底逻辑
                deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        
            # 初始化客户端
            client = OpenAI(
                api_key=deepseek_api_key,
                base_url="https://api.deepseek.com"
            )
        except Exception as e:
            st.error("❌ DeepSeek 客户端初始化失败，请检查 .streamlit/secrets.toml")
            st.stop()
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": PODCAST_PROMPT},
                        {"role": "user", "content": analysis_json_str}
                    ],
                    stream=False
                )
                content = response.choices[0].message.content
                return clean_and_parse_json(content)
            except Exception as e:
                st.error(f"Podcast Script Generation Failed: {e}")
                return None

def synthesize_volcano(text, voice_type, output_file):
    """Synthesizes one segment using Volcano TTS API."""
    url = "https://openspeech.bytedance.com/api/v1/tts"
    header = {"Authorization": f"Bearer; {VOLC_TOKEN}"}
    
    req = {
        "app": {"appid": VOLC_APPID, "token": "access_token", "cluster": CLUSTER},
        "user": {"uid": "user_1"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": 1.2,  # 1.2x Speed
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "text_type": "plain",
            "operation": "query",
        }
    }
    
    try:
        resp = requests.post(url, json=req, headers=header)
        if "data" in resp.json():
            with open(output_file, "wb") as f:
                f.write(base64.b64decode(resp.json()["data"]))
            return True
        else:
            st.error(f"TTS Error: {resp.text}")
            return False
    except Exception as e:
        st.error(f"Request Error: {e}")
        return False

def generate_podcast_volcano_batch(script_list, final_file):
    """Generates and concatenates audio segments using Volcano TTS."""
    segments = []
    
    try:
        progress_bar = st.progress(0)
        total_lines = len(script_list)
        
        for i, line in enumerate(script_list):
            voice = VOICE_ID_MALE if line.get('role') == 'Male' else VOICE_ID_FEMALE
            text = line.get('text', '')
            temp_name = f"temp_{i}.mp3"
            
            if synthesize_volcano(text, voice, temp_name):
                segments.append(temp_name)
            
            progress_bar.progress((i + 1) / total_lines)
            
        # Concatenate
        with open(final_file, "wb") as outfile:
            for seg in segments:
                if os.path.exists(seg):
                    with open(seg, "rb") as infile:
                        outfile.write(infile.read())
                    
    except Exception as e:
        st.error(f"Batch Generation Error: {e}")
    finally:
        # Cleanup
        for seg in segments:
            if os.path.exists(seg):
                os.remove(seg)
                
    return True

# Logic
# 1. Init Session State
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = None
if 'podcast_file' not in st.session_state:
    st.session_state['podcast_file'] = None

if st.button("开始降维打击 (Generate)", key="btn_generate_final"):
    if not (input_mask and input_jealousy and input_image and input_payoff and input_enemy and input_sacrifice and input_loop):
        st.warning("请填满所有空洞，诚实地面对自己。")
    elif not api_key:
        st.error("缺少启动密钥 (API Key)。请在侧边栏输入。")
    else:
        user_prompt = f"""
        # User Input Data (7 Dimensions):
        1. 真面目 (Mask): {input_mask}
        2. 嫉妒心 (Jealousy): {input_jealousy}
        3. 图景 (Image): {input_image}
        4. 红利 (Payoff): {input_payoff}
        5. 紧箍咒 (Enemy): {input_enemy}
        6. 牺牲品 (Sacrifice): {input_sacrifice}
        7. 死循环 (Loop): {input_loop}
        """
        
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        with st.spinner("正在潜入你的潜意识深处... DeepSeek V3.2 思考中..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    stream=False
                )
                
                content = response.choices[0].message.content
                
                # Cleanup markdown
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "")
                elif content.startswith("```"):
                     content = content.replace("```", "")
                
                start_index = content.find('{')
                end_index = content.rfind('}')
                
                if start_index != -1 and end_index != -1:
                    json_str = content[start_index:end_index+1]
                    try:
                        data = json.loads(json_str)
                        st.session_state['analysis_result'] = data  # Save to state
                        st.session_state['podcast_file'] = None     # Reset podcast
                        
                    except json.JSONDecodeError as e:
                        st.error("JSON 解析失败，精神错乱中...")
                        st.text(f"Raw Content:\n{content}")
                else:
                    st.error("未能找到有效的 JSON 结构。")
                    st.text(f"Raw Content:\n{content}")
                    
            except Exception as e:
                st.error(f"发生未知错误: {str(e)}")

# Render if we have results in state
if st.session_state['analysis_result']:
    data = st.session_state['analysis_result']
    
    # Handle nested coordinates safely
    coords = data.get("coordinates", {})
    if isinstance(coords, str): 
        coord_text = coords
    else:
        coord_text = f"**痛苦颗粒度:** {coords.get('pain_level', 'N/A')}<br>**心理画像:** {coords.get('profile', 'N/A')}"

    cards = [
        ("🤡 撕面具 | THE UNMASKING", data.get("unmasking", "N/A")),
        ("🌑 破投射 | SHADOW INTEGRATION", data.get("shadow_integration", "N/A")),
        ("🙈 致命盲区 | THE GLITCH", data.get("blind_spot", "N/A")),
        ("📍 精神坐标 | THE COORDINATES", coord_text),
        ("⚗️ 灵魂炼金术 | THE SUBLIMATION", data.get("sublimation", "N/A")),
        ("⚡ 一分钟微行动 | THE KICK", data.get("micro_action", "N/A"))
    ]
    
    st.markdown("### 🔍 深度分析报告")
    for title, text in cards:
        st.markdown(f"""
        <div class="psych-card">
            <div class="psych-card-title">{title}</div>
            <div>{text}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- Podcast Section ---
    st.divider()
    st.header("🎧 深夜解剖室 (Podcast)")
    st.caption("太扎心了不敢看？不如戴上耳机，听听另外两个人在背后怎么议论你。")

    # If podcast file doesn't exist yet, show generate button
    if st.session_state['podcast_file'] is None:
        if st.button("生成我的专属播客 (Generate Podcast)"):
            with st.spinner("正在录制节目... (火山引擎合成中)"):
                # 1. Generate Script
                script = generate_podcast_script(json.dumps(data, ensure_ascii=False), api_key)
                
                if script:
                    # === 🛡️ 新增的防呆补丁 ===
                    if isinstance(script, str):
                        st.warning("DeepSeek 生成格式有误，正在自动修正...")
                        script = [] 
                    # ========================

                    # 2. Generate Audio (Volcano Batch)
                    audio_file = "podcast_output.mp3"
                    
                    generate_podcast_volcano_batch(script, audio_file)
                    
                    if os.path.exists(audio_file):
                        st.session_state['podcast_file'] = audio_file
                        st.rerun()

    # If podcast file exists, show audio player
    if st.session_state['podcast_file']:
        st.success("节目录制完成！(Powered by Volcano TTS)")
        st.audio(st.session_state['podcast_file'], format="audio/mp3")


