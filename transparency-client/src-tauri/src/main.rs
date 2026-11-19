#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Stdio};

/// Проверка доступности FastAPI (sidecar Python-процесс).
#[tauri::command]
async fn backend_status() -> Result<String, String> {
    let resp = reqwest::get("http://127.0.0.1:8000/health")
        .await
        .map_err(|e| format!("backend недоступен: {e}"))?;
    Ok(format!("{}", resp.status()))
}

/// Запуск backend: ищем соседнюю директорию transparency-api и поднимаем uvicorn через uv.
#[tauri::command]
fn start_backend() -> Result<String, String> {
    let candidates = ["../transparency-api", "../../transparency-api", "../backend", "../../backend"];
    let dir = candidates
        .iter()
        .map(std::path::Path::new)
        .find(|p| p.is_dir())
        .ok_or("не найдена директория backend (transparency-api) рядом с клиентом")?;

    Command::new("uv")
        .args(["run", "uvicorn", "app.main:app", "--port", "8000"])
        .current_dir(dir)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("не удалось запустить backend (нужен uv в PATH): {e}"))?;
    Ok("backend запускается…".into())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![backend_status, start_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
