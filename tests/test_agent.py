"""
Тест агента — работает с langchain 1.2.18 + langgraph 1.1.10
"""
import warnings

# Подавляем предупреждение
warnings.filterwarnings(
    "ignore",
    message="The default value of `allowed_objects` will change",
    module="langgraph.checkpoint.serde.encrypted"
)

from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# --- Инструмент ---
@tool
def get_current_time() -> str:
    """Возвращает текущее время в формате ЧЧ:ММ."""
    from datetime import datetime
    return datetime.now().strftime("%H:%M")

# --- Модель ---
llm = ChatOllama(
    model="llama3.1",
    temperature=0,
    base_url="http://localhost:11434"
)

# --- Промпт ---
system_prompt = "Вы — полезный ассистент. Используйте инструменты, если нужно."
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder("messages"),
])

# --- Агент ---
agent_executor = create_agent(
    model=llm,        # ✅ Было: llm=llm → Стало: model=llm
    tools=[get_current_time],
    system_prompt=system_prompt,
)

# --- Тест ---
result = agent_executor.invoke({
    "messages": [("human", "Который сейчас час?")]
})

print("Ответ:", result["messages"][-1].content)