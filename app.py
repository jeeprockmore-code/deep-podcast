import streamlit as st
import os
import json
import re
import ast
from openai import OpenAI

# ==========================================
# 1. 页面配置 & 极简黑白 UI (强制覆盖暗色模式 + 字体修复)
# ==========================================
st.set_page_config(
    page_title="反矫情战略顾问",
    page_icon="🖤",
    layout="centered",
    initial_sidebar_state="collapsed"  # 侧边栏默认收起，保持界面干净
)

# CSS 修复核心：
# 1. 强制背景白
# 2. 强制所有文字（包括标题、正文、Label）黑
# 3. 强制输入框提示词深灰
st.markdown("""
<style>
    /* 1. 强制全局背景白，文字黑 */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] { 
        background-color: #ffffff !important; 
        color: #000000 !important; 
        font-family: 'Courier New', Courier, monospace; 
    }
    
    /* 2. 🔥 核心修复：强制所有 Label (问题标题) 和 Markdown 文本为黑色 */
    /* 解决手机暗色模式下，标题和正文变成白色导致看不清的问题 */
    label, .stMarkdown, .stMarkdown p, [data-testid="stMarkdownContainer"] p, .stTextArea label {
        color: #000000 !important;
    }

    /* 3. 输入框样式修正 */
    .stTextArea textarea { 
        background-color: #f4f4f4 !important; 
        color: #000000 !important; 
        border: 1px solid #333333 !important; 
        caret-color: #000000 !important; /* 光标颜色 */
    }
    
    /* 4. 强制提示词(Placeholder)颜色为深灰 */
    .stTextArea textarea::placeholder {
        color: #555555 !important;
        opacity: 1 !important; 
        font-weight: normal;
    }
    
    /* 5. 按钮样式 */
    .stButton > button { 
        background-color: #000000 !important; 
        color: #ffffff !important; 
        border: none; 
        width: 100%; 
        padding: 10px; 
        font-weight: bold; 
        transition: all 0.3s; 
    }
    .stButton > button:hover { 
        background-color: #333333 !important; 
        color: #ffffff !important; 
    }
    
    /* 6. 标题样式 */
    h1, h2, h3 { color: #000000 !important; font-weight: 900; }
    
    /* 7. 结果卡片样式 */
    .psych-card { 
        border: 2px solid #000000; 
        padding: 20px; 
        margin-bottom: 20px; 
        background-color: #ffffff; 
        box-shadow: 5px 5px 0px #000000; 
        color: #000000;
    }
    .psych-card-title { 
        font-size: 1.2em; 
        font-weight: bold; 
        margin-bottom: 10px; 
        border-bottom: 1px solid #000000; 
        padding-bottom: 5px; 
        text-transform: uppercase; 
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API Key 配置 (后台静默加载，不显示UI)
# ==========================================
api_key = None

# 优先读取 .streamlit/secrets.toml，其次读取环境变量
if "deepseek" in st.secrets:
    api_key = st.secrets["deepseek"]["api_key"]
elif os.getenv("DEEPSEEK_API_KEY"):
    api_key = os.getenv("DEEPSEEK_API_KEY")

# ==========================================
# 3. 页面标题 & 七维扫描输入区 (文案100%保留)
# ==========================================
st.title("反矫情战略顾问")
st.markdown("**Anti-Hypocrisy Strategy** | *DeepSeek V3.2 驱动 · 专治各种不开心与想不开*")
st.markdown("---")

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
# 4. Prompts (纯文本分析版 - 逐字未动)
# ==========================================
SYSTEM_PROMPT = """
# Role:
你是一位**“反矫情”的心理战略顾问**。你不是心理医生，你是一个看透人性的鬼才导演。你的任务是把用户的人生剧本拿来，指出哪段戏演砸了，哪句台词是撒谎。

# Input Data (七维扫描):
1. 真面目: 用户隐藏的阴暗面。
2. 嫉妒心: 用户的投射（渴望成为的样子）。
3. 图景: 精神状态的画面。
4. 红利: 维持现状的隐秘好处（次级获益）。
5. 紧箍咒: 内在的超我/批判声音。
6. 牺牲品: 被压抑的本我/生命力。
7. 死循环: 用户的惯性行为模式。

# Style Constraints (风格绝对约束):
1. **Length & Depth:** 这一版分析必须**丰满**。每个板块至少输出 **150-200字**。禁止三言两语打发用户。
2. **Vivid & Spicy:** 使用大量的比喻、反讽和黑色幽默。不要说教，要“骂醒”。
3. **Logical Flow:** 将 7 个输入串联成一个完整的侦探故事，不要割裂地分析。

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

# ==========================================
# 5. 核心工具：强力 JSON 解析器
# ==========================================
def parse_json_robust(content):
    if not content: return None
    clean_content = re.sub(r"```json|```", "", content).strip()
    
    # 找 {}
    first_brace = clean_content.find("{")
    
    start = -1
    if first_brace != -1:
        start = first_brace
        
    if start == -1: return None
    
    end = clean_content.rfind("}")
    if end == -1: return None
    
    json_str = clean_content[start:end+1]
    
    try:
        # 尝试宽松解析
        return json.loads(json_str, strict=False)
    except:
        try:
            # 兜底：处理 true/false 小写问题，使用 Python 的 ast
            fixed_str = json_str.replace("true", "True").replace("false", "False").replace("null", "None")
            return ast.literal_eval(fixed_str)
        except:
            return None

# ==========================================
# 6. 主程序逻辑
# ==========================================
if 'analysis_result' not in st.session_state: st.session_state['analysis_result'] = None

# --- 按钮: 深度分析 ---
if st.button("开始降维打击 (Generate)", key="btn_gen"):
    # 检查输入完整性
    if not (input_mask and input_jealousy and input_image and input_payoff and input_enemy and input_sacrifice and input_loop):
        st.warning("请填满所有空洞，诚实地面对自己。")
    elif not api_key:
        # 这里的错误提示只会在 Secrets 没配置对的时候出现
        st.error("❌ 系统错误：未检测到 API Key。请在后台 .streamlit/secrets.toml 中配置 [deepseek] api_key。")
    else:
        # 完整的 Prompt 拼接
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
        with st.spinner("🧠 DeepSeek Reasoner 正在扫描你的潜意识..."):
            try:
                response = client.chat.completions.create(
                    model="deepseek-reasoner",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
                    stream=False
                )
                content = response.choices[0].message.content
                parsed_data = parse_json_robust(content)
                
                if parsed_data:
                    st.session_state['analysis_result'] = parsed_data
                    st.rerun()
                else:
                    st.error("❌ JSON 解析失败，DeepSeek 可能输出了无效格式"); st.caption("原始返回如下："); st.code(content)

            except Exception as e:
                st.error(f"API Error: {e}")

# --- 结果展示 ---
if st.session_state['analysis_result']:
    data = st.session_state['analysis_result']
    coords = data.get("coordinates", {})
    coord_text = coords if isinstance(coords, str) else f"**痛苦颗粒度:** {coords.get('pain_level','N/A')}<br>**心理画像:** {coords.get('profile','N/A')}"

    cards = [
        ("🤡 撕面具 | THE UNMASKING", data.get("unmasking", "")), 
        ("🌑 破投射 | SHADOW INTEGRATION", data.get("shadow_integration", "")),
        ("🙈 致命盲区 | THE GLITCH", data.get("blind_spot", "")), 
        ("📍 精神坐标 | THE COORDINATES", coord_text),
        ("⚗️ 灵魂炼金术 | THE SUBLIMATION", data.get("sublimation", "")), 
        ("⚡ 一分钟微行动 | THE KICK", data.get("micro_action", ""))
    ]
    st.markdown("### 🔍 深度分析报告")
    for t, txt in cards:
        st.markdown(f"<div class='psych-card'><div class='psych-card-title'>{t}</div><div>{txt}</div></div>", unsafe_allow_html=True)
