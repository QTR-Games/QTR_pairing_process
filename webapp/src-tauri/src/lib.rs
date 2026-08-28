use tauri::{
  menu::{AboutMetadata, MenuBuilder, MenuItemBuilder, SubmenuBuilder},
  Emitter,
};
use tauri_plugin_dialog::DialogExt;

/// Write a backup document to a file the user chooses in a native save dialog.
///
/// Returns the saved path, or `None` when the user cancels. The blocking dialog
/// is safe here because an async command runs off the main thread.
#[tauri::command]
async fn save_backup(
  app: tauri::AppHandle,
  contents: String,
  default_name: String,
) -> Result<Option<String>, String> {
  let picked = app
    .dialog()
    .file()
    .set_file_name(&default_name)
    .add_filter("KLIK KLAK backup", &["json"])
    .blocking_save_file();

  match picked {
    Some(file) => {
      let path = file.into_path().map_err(|e| e.to_string())?;
      std::fs::write(&path, contents).map_err(|e| e.to_string())?;
      Ok(Some(path.to_string_lossy().into_owned()))
    }
    None => Ok(None),
  }
}

/// Read the text of a file the user chooses in a native open dialog.
///
/// Returns `None` when the user cancels.
#[tauri::command]
async fn open_backup(app: tauri::AppHandle) -> Result<Option<String>, String> {
  let picked = app
    .dialog()
    .file()
    .add_filter("KLIK KLAK backup", &["json"])
    .blocking_pick_file();

  match picked {
    Some(file) => {
      let path = file.into_path().map_err(|e| e.to_string())?;
      let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
      Ok(Some(text))
    }
    None => Ok(None),
  }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_sql::Builder::default().build())
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_window_state::Builder::default().build())
    .invoke_handler(tauri::generate_handler![save_backup, open_backup])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      build_menu(app)?;
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

/// The desktop menu bar.
///
/// File carries the two data actions (save/open a backup) with the accelerators
/// a desktop user reaches for, Edit exposes the platform's native clipboard
/// editing so text fields behave like a real app rather than a web page, and
/// Help shows an About box. The board data lives in the frontend, so the two
/// backup items do not act here: they emit `menu://…` events that the webview
/// listens for and runs through the very same code path as the on-screen
/// buttons, keeping one implementation of "save" and "open".
fn build_menu(app: &tauri::App) -> tauri::Result<()> {
  let save = MenuItemBuilder::with_id("backup-save", "Save Backup…")
    .accelerator("CmdOrCtrl+S")
    .build(app)?;
  let open = MenuItemBuilder::with_id("backup-open", "Open Backup…")
    .accelerator("CmdOrCtrl+O")
    .build(app)?;

  let file = SubmenuBuilder::new(app, "File")
    .item(&save)
    .item(&open)
    .separator()
    .quit()
    .build()?;

  // cut/copy/paste/select-all are the cross-platform predefined items; undo and
  // redo are deliberately omitted because they are macOS-only.
  let edit = SubmenuBuilder::new(app, "Edit")
    .cut()
    .copy()
    .paste()
    .select_all()
    .build()?;

  let about = AboutMetadata {
    name: Some("KLIK KLAK".into()),
    version: Some(env!("CARGO_PKG_VERSION").into()),
    comments: Some("QTR 5v5 tournament pairing planner".into()),
    ..Default::default()
  };
  let help = SubmenuBuilder::new(app, "Help").about(Some(about)).build()?;

  let menu = MenuBuilder::new(app)
    .item(&file)
    .item(&edit)
    .item(&help)
    .build()?;

  app.set_menu(menu)?;

  app.on_menu_event(|handle, event| match event.id.0.as_str() {
    "backup-save" => {
      let _ = handle.emit("menu://backup-save", ());
    }
    "backup-open" => {
      let _ = handle.emit("menu://backup-open", ());
    }
    _ => {}
  });

  Ok(())
}
