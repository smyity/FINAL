import os
import datetime
import subprocess
import clickhouse_connect
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse


app = FastAPI()

# подключение к ClickHouse (хост совпадает с именем сервиса в compose)
def get_clickhouse_client():

    clickhouse_user = os.getenv("CLICKHOUSE_USER")
    clickhouse_pass = os.getenv("CLICKHOUSE_PASSWORD")

    return clickhouse_connect.get_client(
        host='clickhouse',
        username=clickhouse_user,
        password=clickhouse_pass
    )


# Инициализация таблицы при старте
# +-----------+-----------+--------------+------------+
# | timestamp | cpu_usage | memory_usage | disk_usage |
# +-----------+-----------+--------------+------------+
try:
    client = get_clickhouse_client()
    client.command('''
        CREATE TABLE IF NOT EXISTS win_metrics (
            timestamp DateTime64(3),
            computer_name String,
            cpu_usage Float32,
            memory_usage Float32,
            disk_usage Float32
        ) ENGINE = MergeTree()
        ORDER BY (computer_name, timestamp)
    ''')
except Exception as e:
    print(f"Ошибка инициализации ClickHouse: {e}")

class Metrics(BaseModel):
    computer_name: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float


# шаблон создаваемого скрипта отправки метрик
AGENT_CODE_TEMPLATE = """package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"time"
	"os"
	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/mem"
)

type Metrics struct {{
	ComputerName string `json:"computer_name"`
	CpuUsage    float64 `json:"cpu_usage"`
	MemoryUsage float64 `json:"memory_usage"`
	DiskUsage   float64 `json:"disk_usage"`
}}

func main() {{
	serverURL := "http://{SERVER_IP}:1111/api/metrics"

	hostname, err := os.Hostname()
	if err != nil {{
		hostname = "unknown_windows_pc"
	}}

	for {{
		cpuPercentages, _ := cpu.Percent(time.Second, false)
		cpuUsage := 0.0
		if len(cpuPercentages) > 0 {{
			cpuUsage = cpuPercentages[0]
		}}

		vMem, _ := mem.VirtualMemory()
		dUsage, _ := disk.Usage("C:\\\\")

		payload := Metrics{{
            ComputerName: hostname,
			CpuUsage:    cpuUsage,
			MemoryUsage: vMem.UsedPercent,
			DiskUsage:   dUsage.UsedPercent,
		}}

		jsonData, _ := json.Marshal(payload)
		resp, err := http.Post(serverURL, "application/json", bytes.NewBuffer(jsonData))
		if err == nil {{
			resp.Body.Close()
		}}

		time.Sleep(60 * time.Second) // Интервал сбора (1 минута)
	}}
}}
"""


# создание, компиляция и скачивание установочного файла
@app.get("/api/installer")
def create_and_get_install_file():
    server_ip = os.getenv("SERVER_IP", "127.0.0.1")
    go_filename = "main.go"
    exe_filename = "monitoring_agent.exe"

    try:
        configured_code = AGENT_CODE_TEMPLATE.format(SERVER_IP=server_ip)
        with open(go_filename, "w", encoding="utf-8") as f:
            f.write(configured_code)

        # передать переменные окружения GOOS и GOARCH в процесс сборки
        env = os.environ.copy()
        env["GOOS"] = "windows"
        env["GOARCH"] = "amd64"
        env["GOCACHE"] = "/root/.cache/go-build"
        env["GOPATH"] = "/go"

        subprocess.run(
            ["go", "mod", "tidy"],
            capture_output=True,
            env=env,
            timeout=10
        )

        compile_command = [
            "go",
            "build",
            "-buildmode=exe",
            "-o",
            exe_filename,
            go_filename,
        ]

        print("Начало компиляции Go агента...")
        subprocess.check_output(compile_command, env=env, timeout=30)
        print("Компиляция успешно завершена, файл готов к отправке.")

        # вернуть готовый бинарник для Windows
        return FileResponse(
            path=exe_filename,
            filename="monitoring_agent.exe", # под каким именем файл скачается у пользователя
            media_type="application/octet-stream",
        )

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Превышено время ожидания компиляции агента.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}"
        )
    finally:
        # удалить временный .py файл, exe удалять нельзя!
        if os.path.exists(go_filename):
            os.remove(go_filename)


# прием метрик
@app.post("/api/metrics")
def receive_metrics(data: Metrics):
    try:
        client = get_clickhouse_client()
        current_time = datetime.datetime.now(datetime.timezone.utc)
        data_to_insert = [[current_time, data.computer_name, data.cpu_usage, data.memory_usage, data.disk_usage]]
        client.insert('win_metrics', data_to_insert, column_names=['timestamp', 'computer_name', 'cpu_usage', 'memory_usage', 'disk_usage'])
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка записи в базу данных: {str(e)}")


# список активных компьютеров
@app.get("/api/computers")
def get_computers_list():
    try:
        client = get_clickhouse_client()
        result = client.query("SELECT DISTINCT computer_name FROM win_metrics")
        return [row[0] for row in result.result_rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
def get_history(
    computer: str = Query(..., description="Имя компьютера"),
    start: str = Query(..., description="ISO timestamp начала интервала"),
    end: str = Query(..., description="ISO timestamp конца интервала")
):
    try:
        client = get_clickhouse_client()
        try:
            start_clean = start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            end_clean = end.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        except Exception:
            start_clean = start.replace("T", " ").split("+")[0].split("Z")[0]
            end_clean = end.replace("T", " ").split("+")[0].split("Z")[0]

        query = '''
            SELECT timestamp, cpu_usage, memory_usage, disk_usage 
            FROM win_metrics 
            WHERE computer_name = {computer:String} AND timestamp >= {start:String} AND timestamp <= {end:String}
            ORDER BY timestamp ASC
        '''
    
        result = client.query(query, parameters={'computer': computer, 'start': start_clean, 'end': end_clean})

        # ответ в удобной для фронтенда структуре
        response_data = {"time": [], "cpu": [], "ram": [], "disk": []}
        for row in result.result_rows:
            # перевод timestamp в строку для JSON
            response_data["time"].append(row[0].strftime("%Y-%m-%d %H:%M:%S"))
            response_data["cpu"].append(round(row[1], 1))
            response_data["ram"].append(round(row[2], 1))
            response_data["disk"].append(round(row[3], 1))

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения истории: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1111)