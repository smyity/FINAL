import datetime
import requests
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Windows Мониторинг + ClickHouse", layout="wide")
st.title("Метрики компьютера")

BACKEND_URL = "http://localhost:1111/api/history"
BACKEND_COMPUTERS_URL = "http://localhost:1111/api/computers"
BACKEND_INSTALLER_URL = "http://localhost:1111/api/installer"

# боковая панель
st.sidebar.header("Фильтры")

try:
    comp_response = requests.get(BACKEND_COMPUTERS_URL, timeout=2)
    computers_list = comp_response.json() if comp_response.status_code == 200 else []
except Exception:
    computers_list = []

# выпадающий список выбора компьютера
if computers_list:
    selected_computer = st.sidebar.selectbox("Выберите компьютер для мониторинга:", computers_list)
else:
    selected_computer = None
    st.sidebar.info("Ожидание подключения первого ПК...")

# выбор интервала
time_range = st.sidebar.selectbox(
    "Выберите интервал:",
    ["Последний час", "Последние 6 часов", "Последние 24 часа", "За все время"]
)


@st.cache_data(show_spinner="Генерация и компиляция Windows-агента...")
def download_agent_bytes():
    try:
        response = requests.get(BACKEND_INSTALLER_URL, timeout=310)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Не удалось собрать файл. Ошибка бэка: {response.text}")
            return None
    except Exception as e:
        st.error(f"Ошибка подключения к бэкенду: {e}")
        return None


# определить временные рамки в формате ISO
now = datetime.datetime.now(datetime.timezone.utc)
if time_range == "Последний час":
    start_time = now - datetime.timedelta(hours=1)
elif time_range == "Последние 6 часов":
    start_time = now - datetime.timedelta(hours=6)
elif time_range == "Последние 24 часа":
    start_time = now - datetime.timedelta(hours=24)
else:
    start_time = now - datetime.timedelta(days=365)


try:
    # отправление параметров фильтрации на бэкенд
    params = {"start": start_time.isoformat(), "end": now.isoformat()}
    response = requests.get(BACKEND_URL, params=params, timeout=3)
    metrics_db = response.json() if response.status_code == 200 else {}
except Exception:
    metrics_db = {}

metrics_db = {}
if selected_computer:
    try:
        params = {
            "computer": selected_computer,  # Передаем выбранный ПК
            "start": start_time.isoformat(), 
            "end": now.isoformat()
        }
        response = requests.get(BACKEND_URL, params=params, timeout=3)
        if response.status_code == 200:
            metrics_db = response.json()
    except Exception:
        pass


### Кнопка скачивания exe файла ###
agent_bytes = download_agent_bytes()

if agent_bytes:
    st.download_button(
        label="Скачать установочный файл для Windows",
        data=agent_bytes,
        file_name="monitoring_agent.exe",
        mime="application/octet-stream",
    )

### отображение графиков ###
if metrics_db and metrics_db.get("time"):
    # текущие показатели
    last_cpu = metrics_db["cpu"][-1]
    last_ram = metrics_db["ram"][-1]
    last_disk = metrics_db["disk"][-1]

    st.subheader(f"Текущее состояние: {selected_computer}")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Последний CPU", value=f"{last_cpu} %")
    col2.metric(label="Последний RAM", value=f"{last_ram} %")
    col3.metric(label="Последний Disk", value=f"{last_disk} %")

    st.subheader(f"Графики за интервал: {time_range}")

    df = pd.DataFrame({
        "Время": pd.to_datetime(metrics_db["time"]),
        "Процессор (CPU)": metrics_db["cpu"],
        "Память (RAM)": metrics_db["ram"],
        "Диск (Disk)": metrics_db["disk"]
    })
    df.set_index("Время", inplace=True)
    # интерактивный график
    st.line_chart(df)
else:
    st.info("Нет данных за выбранный период. Проверьте, запущен ли скрипт на Windows.")

# кнопка ручного обновления интерфейса
if st.button("Обновить"):
    st.rerun()