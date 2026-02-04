import streamlit as st
import os
import json
import requests
import uuid
import base64
import re
import ast
from openai import OpenAI

# ==========================================
# 1. 页面配置 & CSS (保留了你的极简黑白风)
# ==========================================
st.set_page_config(
    page_title="反矫情战略顾问",
    page_icon="🖤",
    layout="centered",
    initial_sidebar_state="expanded"
)

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
    
    /* Custom Cards (保留了你的卡片样式) */
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

# ==========================================
# 2. 侧边栏 & 密钥配置
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("DeepSeek API Key", type="password", help="Enter your DeepSeek API Key here.")
    
    # 自动加载逻辑
    if not api_key:
        if "deepseek" in st.secrets:
            api_key = st.secrets["deepseek"]["api_key"]
            st.success("已自动加载云端密钥！")
        elif os.getenv("DEEPSEEK_API_KEY"):
            api_key = os.getenv("DEEPSEEK_API_KEY")
            
# Main Header
st.title("反矫情战略顾问")
st.markdown("**Anti-Hypocrisy Strategy** | *DeepSeek V3.2 驱动 · 专治各种不开心与想不开*")
st.markdown("---")

# ==========================================
# 3. 输入区域 (七维扫描)
# ==========================================
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

# ==========================================
# 4. Prompts (保留了你的核心 Prompt)
# ==========================================
SYSTEM_PROMPT = """
# Role:
你是一位**“反矫情”的心理战略顾问**。你不是心理医生，你是一个看透人性的鬼才导演。你的任务是把用户的人生剧本拿来，指出哪段戏演砸了，哪句台词是撒谎。

# Input Data (七维扫描):
1.  真面目: 用户隐藏的阴暗面。
2.  嫉妒心: 用户的投射（渴望成为的样子）。
3.  图景: 精神状态的画面。
4.  红利: 维持现状的隐秘好处（次级获益）。
5.  紧箍咒: 内在的超我/批判声音。
6.  牺牲品: 被压抑的本我/生命力。
7.  死循环: 用户的惯性行为模式。

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
# 5. 核心功能函数 (DeepSeek + 清洗 + 兼容列表)
# ==========================================
def generate_podcast_script(analysis_json_str, api_key):
    """Generates the podcast script using DeepSeek with list/object compatibility."""
    import json
    import re
    import os
    from openai import OpenAI
    import streamlit as st

    # 初始化客户端
    try:
        final_key = api_key
        if not final_key and "deepseek" in st.secrets:
            final_key = st.secrets["deepseek"]["api_key"]
        if not final_key:
            final_key = os.getenv("DEEPSEEK_API_KEY", "")
            
        client = OpenAI(api_key=final_key, base_url="https://api.deepseek.com")
    except Exception as e:
        st.error(f"DeepSeek Client Init Failed: {e}")
        return None

    # 生成剧本
    try:
        response = client.chat.completions.create(
            model="deepseek-chat", 
            messages=[
                {"role": "system", "content": PODCAST_PROMPT},
                {"role": "user", "content": analysis_json_str}
            ],
            stream=False,
            temperature=1.3 
        )
        content = response.choices[0].message.content
        
        # --- 万能清洗逻辑 ---
        content_clean = re.sub(r"```json|```", "", content).strip()
        
        # 同时寻找 [ 和 {
        first_bracket = content_clean.find("[")
        first_brace = content_clean.find("{")
        
        start = -1
        if first_bracket != -1 and first_brace != -1:
            start = min(first_bracket, first_brace)
        elif first_bracket != -1:
            start = first_bracket
        elif first_brace != -1:
            start = first_brace
            
        end = max(content_clean.rfind("]"), content_clean.rfind("}"))
        
        if start != -1 and end != -1:
            json_str = content_clean[start:end+1]
            data = json.loads(json_str)
            
            # 兼容性补丁：统一返回字典
            if isinstance(data, list):
                return {"podcast": data}
            else:
                return data
        else:
            st.warning("⚠️ 无法识别 JSON 结构，DeepSeek 返回原始内容如下：")
            st.code(content)
            return None
            
    except json.JSONDecodeError as e:
        st.error("❌ JSON 解析失败")
        st.caption("DeepSeek 的原始回复如下：")
        st.code(content) 
        return None
    except Exception as e:
        st.error(f"生成过程发生未知错误: {e}")
        return None

# ==========================================
# 6. 主逻辑控制 (Session State + Reasoner)
# ==========================================

# 初始化大脑记忆
if 'analysis_result' not in st.session_state:
    st.session_state['analysis_result'] = None
if 'podcast_file' not in st.session_state:
    st.session_state['podcast_file'] = None

# --- 阶段一：开始降维打击 (DeepSeek Reasoner) ---
if st.button("开始降维打击 (Generate)", key="btn_generate_final"):
    if not (input_mask and input_jealousy and input_image and input_payoff and input_enemy and input_sacrifice and input_loop):
        st.warning("请填满所有空洞，诚实地面对自己。")
    elif not api_key:
        st.error("❌ 缺少启动密钥 (API Key)。请在侧边栏输入。")
    else:
        # 组装 Prompt
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
        
        # 调用 DeepSeek (DeepSeek Reasoner 保留！)
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
                
                # 清洗 Markdown
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "")
                elif content.startswith("```"):
                     content = content.replace("```", "")
                
                # 提取 JSON
                start_index = content.find('{')
                end_index = content.rfind('}')
                
                if start_index != -1 and end_index != -1:
                    json_str = content[start_index:end_index+1]
                    try:
                        data = json.loads(json_str)
                        st.session_state['analysis_result'] = data
                        st.session_state['podcast_file'] = None 
                        st.rerun() 
                    except json.JSONDecodeError:
                        st.error("JSON 解析失败")
                        st.text(content)
                else:
                    st.error("未能找到有效的 JSON 结构")
                    st.text(content)
                    
            except Exception as e:
                st.error(f"发生未知错误: {str(e)}")

# --- 阶段二：结果展示 & 播客生成 ---
if st.session_state['analysis_result']:
    data = st.session_state['analysis_result']
    
    # 显示卡片 (保留了你的 CSS 样式)
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

    # 播客生成区域
    st.divider()
    st.header("🎧 深夜解剖室 (Podcast)")
    st.caption("太扎心了不敢看？不如戴上耳机，听听另外两个人在背后怎么议论你。")

    if st.session_state['podcast_file'] is None:
        if st.button("生成我的专属播客 (Generate Podcast)"):
            
            if "volcano" not in st.secrets:
                st.error("❌ 缺少火山引擎配置！请检查 .streamlit/secrets.toml")
            else:
                APPID = st.secrets["volcano"]["appid"]
                TOKEN = st.secrets["volcano"]["token"]
                CLUSTER = "volcano_tts"
                
                # ✅ 干净的 URL，修复了隐形字符问题
                VOLCANO_URL = "[https://openspeech.bytedance.com/api/v1/tts](https://openspeech.bytedance.com/api/v1/tts)"

                with st.spinner("✍️ 正在撰写剧本 (DeepSeek)..."):
                    import json
                    script_data = generate_podcast_script(json.dumps(data, ensure_ascii=False), api_key)
                    
                    if not script_data:
                        st.error("剧本生成失败")
                        podcast_items = []
                    elif isinstance(script_data, dict):
                         podcast_items = script_data.get("podcast", [])
                    elif isinstance(script_data, list):
                         podcast_items = script_data
                    else:
                         podcast_items = []

                if podcast_items:
                    with st.spinner(f"🎙️ 正在录制 {len(podcast_items)} 段对话..."):
                        try:
                            import requests
                            import base64
                            
                            full_audio_data = b""
                            progress_bar = st.progress(0)
                            
                            for i, item in enumerate(podcast_items):
                                text = item["text"]
                                role = item["role"]
                                voice_type = "BV004_streaming" if role == "Female" else "BV001_streaming"
                                
                                header = {"Authorization": f"Bearer; {TOKEN}"}
                                request_json = {
                                    "app": {"appid": APPID, "token": "access_token", "cluster": CLUSTER},
                                    "user": {"uid": "user_1"},
                                    "audio": {
                                        "voice_type": voice_type,
                                        "encoding": "mp3",
                                        "speed_ratio": 1.0, "volume_ratio": 1.0, "pitch_ratio": 1.0,
                                    },
                                    "request": {
                                        "text": text, "text_type": "plain", "operation": "query",
                                        "with_frontend": 1, "frontend_type": "unitTson"
                                    }
                                }
                                
                                resp = requests.post(VOLCANO_URL, json=request_json, headers=header)
                                
                                if "data" in resp.json():
                                    full_audio_data += base64.b64decode(resp.json()["data"])
                                progress_bar.progress((i + 1) / len(podcast_items))
                            
                            output_filename = "podcast_output.mp3"
                            with open(output_filename, "wb") as f:
                                f.write(full_audio_data)
                            
                            st.session_state['podcast_file'] = output_filename
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"音频合成错误: {e}")
                else:
                    st.warning("生成的剧本为空")

    # 播放器
    if st.session_state['podcast_file']:
        st.success("🎉 节目录制完成！(Powered by Volcano TTS)")
        st.audio(st.session_state['podcast_file'], format="audio/mp3")
        
        if st.button("🔄 重新生成播客"):
            st.session_state['podcast_file'] = None
            st.rerun()
