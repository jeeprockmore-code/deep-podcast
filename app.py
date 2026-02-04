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
# 1. 页面配置 & 极简黑白 UI
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
    .stApp { background-color: #ffffff; color: #000000; font-family: 'Courier New', Courier, monospace; }
    /* Input Fields */
    .stTextArea textarea { background-color: #f0f0f0; color: #000000; border: 1px solid #000000; }
    /* Buttons */
    .stButton > button { background-color: #000000; color: #ffffff; border: none; width: 100%; padding: 10px; font-weight: bold; transition: all 0.3s; }
    .stButton > button:hover { background-color: #333333; color: #ffffff; }
    /* Titles */
    h1, h2, h3 { color: #000000; font-weight: 900; }
    /* Custom Cards */
    .psych-card { border: 2px solid #000000; padding: 20px; margin-bottom: 20px; background-color: #ffffff; box-shadow: 5px 5px 0px #000000; }
    .psych-card-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #000000; padding-bottom: 5px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 特调参数区 (音色已确认)
# ==========================================
VOICE_ID_FEMALE = "BV700_V2_streaming"  # 莎莎(毒舌版)
VOICE_ID_MALE = "BV102_streaming"       # 阿强(憨厚版)
CLUSTER = "volcano_tts"

# 启动自检
if "volcano" not in st.secrets:
    st.warning("⚠️ 警告：Secrets 中未找到 [volcano] 配置，无法生成语音。")

# ==========================================
# 3. 侧边栏
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("DeepSeek API Key", type="password")
    
    if not api_key:
        if "deepseek" in st.secrets:
            api_key = st.secrets["deepseek"]["api_key"]
            st.success("☁️ 已自动加载云端密钥")
        elif os.getenv("DEEPSEEK_API_KEY"):
            api_key = os.getenv("DEEPSEEK_API_KEY")

st.title("反矫情战略顾问")
st.markdown("**Anti-Hypocrisy Strategy** | *DeepSeek V3.2 驱动 · 专治各种不开心与想不开*")
st.markdown("---")

# ==========================================
# 4. 七维扫描输入区 (完整版)
# ==========================================
st.subheader("🕵️ 七维心理扫描 (Seven-Dimensional Scan)")
col1, col2 = st.columns(2)

with col1:
    input_mask = st.text_area("**1. 【测真面目】**\n剥离社交滤镜后，我性格里真实、甚至阴暗的一面是：", placeholder="例：冷漠 / 精于算计 / 极度自私...", height=130)
    input_jealousy = st.text_area("**2. 【测嫉妒心】**\n我特别看不惯 ______ 的人，但深夜觉得他们活得比我爽。", placeholder="例：那些不努力却运气好的人...", height=130)
    input_image = st.text_area("**3. 【测精神图景】**\n把我的精神状态画成一幅画，画面里是：", placeholder="例：在悬崖边骑独轮车...", height=130)
    input_loop = st.text_area("**4. 【测死循环】**\n我总是陷入死循环：每当 ______ 时，就忍不住 ______ 。", placeholder="例：压力大时暴食，事后又后悔...", height=130)

with col2:
    input_payoff = st.text_area("**5. 【测隐性红利】**\n如果立刻改变，我就不得不失去 ______ 的‘特权’。", placeholder="例：不用承担养家的责任 / 可以继续当受害者...", height=130)
    input_enemy = st.text_area("**6. 【测紧箍咒】**\n脑子里有个声音指责说：‘你如果不 ______ ，你就是废物。’", placeholder="例：如果不年入百万 / 如果不讨好所有人...", height=130)
    input_sacrifice = st.text_area("**7. 【测牺牲品】**\n为了维持和平，我正在亲手扼杀掉那个 ______ 的自己。", placeholder="例：想去流浪的自己 / 有攻击性的自己...", height=130)

# ==========================================
# 5. Prompts (完整结构化版)
# ==========================================
SYSTEM_PROMPT = """
# Role:
你是一位“反矫情”的心理战略顾问。不是心理医生，是看透人性的鬼才导演。
# Input Data (七维扫描):
1. 真面目 2. 嫉妒心 3. 图景 4. 红利 5. 紧箍咒 6. 牺牲品 7. 死循环
# Style:
1. Length: 每板块 150+ 字，丰满。
2. Tone: 毒舌、反讽、黑色幽默、骂醒用户。
3. Logic: 串联成完整的侦探故事。
# Output (JSON Only):
{
  "unmasking": "...", "shadow_integration": "...", "blind_spot": "...",
  "coordinates": { "pain_level": "...", "profile": "..." },
  "sublimation": "...", "micro_action": "..."
}
"""

PODCAST_PROMPT = """
# Role:
《深夜解剖室》制作人。将分析报告改编成极其生活化的男女闲聊。
# Characters:
1. 阿强(男): 捧哏，反应慢。
2. 莎莎(女): 毒舌，看透一切。
# Constraints:
禁止翻译腔，像撸串聊天。
# Output (JSON List):
[{"role": "Male", "text": "..."}, {"role": "Female", "text": "..."}]
"""

# ==========================================
# 6. 核心工具：强力 JSON 解析器 (关键修复点!)
# ==========================================
def parse_json_robust(content):
    """
    专治 DeepSeek 各种不规范 JSON 返回。
    1. 去除 Markdown 符号
    2. 允许字符串内换行 (strict=False)
    3. 兼容单引号和布尔值差异
    """
    if not content:
        return None
        
    # 1. 移除 Markdown 代码块标记
    clean_content = re.sub(r"```json|```", "", content).strip()
    
    # 2. 寻找 JSON 的核心部分 { ... } 或 [ ... ]
    first_brace = clean_content.find("{")
    first_bracket = clean_content.find("[")
    
    start = -1
    # 找最早出现的起始符
    if first_brace != -1 and first_bracket != -1:
        start = min(first_brace, first_bracket)
    elif first_brace != -1:
        start = first_brace
    elif first_bracket != -1:
        start = first_bracket
        
    if start == -1:
        return None
        
    # 找最后的结束符
    end = max(clean_content.rfind("}"), clean_content.rfind("]"))
    if end == -1:
        return None
        
    json_str = clean_content[start:end+1]
    
    # 3. 尝试标准解析 (开启 strict=False 以允许换行符!)
    try:
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        # 4. 如果失败，尝试修正布尔值并用 AST 解析 (兜底方案)
        try:
            # 将 JSON 的 true/false/null 替换为 Python 的 True/False/None
            fixed_str = json_str.replace("true", "True").replace("false", "False").replace("null", "None")
            return ast.literal_eval(fixed_str)
        except:
            return None

def generate_podcast_script(analysis_json_str, api_key):
    """DeepSeek Chat + Robust Parsing."""
    try:
        final_key = api_key
        if not final_key and "deepseek" in st.secrets:
            final_key = st.secrets["deepseek"]["api_key"]
        
        client = OpenAI(api_key=final_key, base_url="https://api.deepseek.com")
        
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
        
        # 使用强力解析器
        data = parse_json_robust(content)
        
        if data:
            if isinstance(data, list): return {"podcast": data}
            return data
        else:
            st.warning("⚠️ 剧本生成：无法识别 JSON"); st.code(content); return None
            
    except Exception as e:
        st.error(f"剧本生成错误: {e}")
        return None

# ==========================================
# 7. 主程序逻辑
# ==========================================
if 'analysis_result' not in st.session_state: st.session_state['analysis_result'] = None
if 'podcast_file' not in st.session_state: st.session_state['podcast_file'] = None

# --- 按钮 1: 深度分析 (DeepSeek Reasoner) ---
if st.button("开始降维打击 (Generate)", key="btn_gen"):
    if not (input_mask and input_jealousy and input_image):
        st.warning("请至少填满前三个核心空洞，否则 DeepSeek 无法下嘴。")
    elif not api_key:
        st.error("❌ 缺少 API Key")
    else:
        # 完整的结构化 Prompt
        user_prompt = f"""
        # User Input Data:
        1. 真面目: {input_mask}
        2. 嫉妒心: {input_jealousy}
        3. 图景: {input_image}
        4. 红利: {input_payoff}
        5. 紧箍咒: {input_enemy}
        6. 牺牲品: {input_sacrifice}
        7. 死循环: {input_loop}
        """
        
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        with st.spinner("🧠 DeepSeek Reasoner 正在扫描你的潜意识..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                    stream=False
                )
                content = response.choices[0].message.content
                
                # 🔥 使用强力解析器处理分析结果
                parsed_data = parse_json_robust(content)
                
                if parsed_data:
                    st.session_state['analysis_result'] = parsed_data
                    st.session_state['podcast_file'] = None # 重置音频
                    st.rerun()
                else:
                    st.error("❌ JSON 解析失败"); st.caption("原始返回如下，可能是格式太乱："); st.code(content)

            except Exception as e:
                st.error(f"API Error: {e}")

# --- 结果展示 & 播客生成 ---
if st.session_state['analysis_result']:
    data = st.session_state['analysis_result']
    coords = data.get("coordinates", {})
    coord_text = coords if isinstance(coords, str) else f"**痛苦颗粒度:** {coords.get('pain_level','N/A')}<br>**心理画像:** {coords.get('profile','N/A')}"

    cards = [
        ("🤡 撕面具", data.get("unmasking", "")), ("🌑 破投射", data.get("shadow_integration", "")),
        ("🙈 致命盲区", data.get("blind_spot", "")), ("📍 精神坐标", coord_text),
        ("⚗️ 灵魂炼金术", data.get("sublimation", "")), ("⚡ 一分钟微行动", data.get("micro_action", ""))
    ]
    st.markdown("### 🔍 深度分析报告")
    for t, txt in cards:
        st.markdown(f"<div class='psych-card'><div class='psych-card-title'>{t}</div><div>{txt}</div></div>", unsafe_allow_html=True)

    st.divider(); st.header("🎧 深夜解剖室 (Podcast)")

    if st.session_state['podcast_file']:
        st.success("🎉 节目录制完成！")
        st.audio(st.session_state['podcast_file'], format="audio/mp3")
        if st.button("🔄 重新生成"): st.session_state['podcast_file'] = None; st.rerun()
    else:
        # --- 按钮 2: 生成播客 (TTS) ---
        if st.button("生成我的专属播客 (Generate Podcast)"):
            if "volcano" not in st.secrets:
                st.error("❌ 缺少火山引擎配置")
            else:
                APPID = st.secrets["volcano"]["appid"]
                TOKEN = st.secrets["volcano"]["token"]
                VOLCANO_URL = "https://openspeech.bytedance.com/api/v1/tts" # 干净 URL

                with st.spinner("✍️ DeepSeek 正在撰写剧本..."):
                    import json
                    script_data = generate_podcast_script(json.dumps(data, ensure_ascii=False), api_key)
                    items = script_data.get("podcast", []) if script_data else []

                if items:
                    with st.spinner(f"🎙️ 火山引擎正在录制 {len(items)} 段对话..."):
                        try:
                            full_audio = b""
                            progress_bar = st.progress(0)
                            
                            for i, item in enumerate(items):
                                # 1. 准备参数
                                voice = VOICE_ID_FEMALE if item["role"] == "Female" else VOICE_ID_MALE
                                header = {"Authorization": f"Bearer; {TOKEN}"}
                                req_json = {
                                    "app": {"appid": APPID, "token": "access_token", "cluster": CLUSTER},
                                    "user": {"uid": "user_1"},
                                    "audio": {
                                        "voice_type": voice,
                                        "encoding": "mp3",
                                        "speed_ratio": 1.2,
                                        "volume_ratio": 1.0, "pitch_ratio": 1.0
                                    },
                                    "request": {"text": item["text"], "text_type": "plain", "operation": "query", "with_frontend": 1, "frontend_type": "unitTson"}
                                }
                                
                                # 2. 发送请求 (干净的 URL)
                                resp = requests.post("https://openspeech.bytedance.com/api/v1/tts", json=req_json, headers=header)
                                resp_data = resp.json()
                                
                                # 3. 🔥 错误侦测：如果失败，直接把原因打印到屏幕上！
                                if "data" in resp_data:
                                    full_audio += base64.b64decode(resp_data["data"])
                                else:
                                    st.error(f"⚠️ 第 {i+1} 句合成失败！火山引擎返回：{resp_data}")
                                
                                progress_bar.progress((i+1)/len(items))
                            
                            # 4. 保存音频
                            if len(full_audio) > 0:
                                with open("podcast.mp3", "wb") as f: f.write(full_audio)
                                st.session_state['podcast_file'] = "podcast.mp3"; st.rerun()
                            else:
                                st.error("❌ 所有音频片段均合成失败，请检查上方红框里的错误信息！")
                                
                        except Exception as e: 
                            st.error(f"合成程序崩溃: {e}") # 👈 刚才缺的就是这一块！
                else: 
                    st.warning("剧本为空或解析失败")

