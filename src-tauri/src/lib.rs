#[tauri::command]
async fn send_invoice_email(
  host: String,
  port: u16,
  username: String,
  password: String,
  from_name: String,
  to_email: String,
  subject: String,
  body: String,
) -> Result<(), String> {
  use lettre::message::header::ContentType;
  use lettre::transport::smtp::authentication::Credentials;
  use lettre::{Message, SmtpTransport, Transport};

  let email = Message::builder()
    .from(
      format!("{from_name} <{username}>")
        .parse()
        .map_err(|e| format!("Invalid from address: {e}"))?,
    )
    .to(
      to_email
        .parse()
        .map_err(|e| format!("Invalid recipient: {e}"))?,
    )
    .subject(subject)
    .header(ContentType::TEXT_PLAIN)
    .body(body)
    .map_err(|e| format!("Could not build email: {e}"))?;

  let creds = Credentials::new(username, password);
  let mailer = SmtpTransport::starttls_relay(&host)
    .map_err(|e| format!("SMTP connection failed: {e}"))?
    .port(port)
    .credentials(creds)
    .build();

  mailer
    .send(&email)
    .map_err(|e| format!("SMTP send failed: {e}"))?;
  Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_fs::init())
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![send_invoice_email])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
