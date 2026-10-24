from google.cloud import firestore
from datetime import datetime, timezone, timedelta
import re
import dateparser  # Menambahkan library untuk parsing tanggal natural

# WIB = UTC+7 (Asia/Jakarta) — digunakan untuk default timezone parsing
_WIB = timezone(timedelta(hours=7))
_UTC = timezone.utc

# --- Helper function: Parse berbagai format tanggal ---
def parse_due_date_any(s: str):
    """
    Parse tanggal/waktu natural (Indonesia & English) dengan timezone WIB.

    - Jika user menyebut jam ("jam 10", "10:00", "pukul 9") → pakai jam tersebut tepat
    - Jika hanya tanggal ("besok", "minggu depan") → default jam 09:00 WIB
    - Selalu return timezone-aware datetime (WIB) agar Firestore simpan UTC yang benar
    """
    if not s:
        return None

    # ── Normalisasi 1: titik → titik dua untuk format jam ───────────────────
    # "10.47" → "10:47", "09.00" → "09:00"
    s = re.sub(
        r'(?<!\d)(\d{1,2})\.(\d{2})(?!\d)',
        lambda m: f"{m.group(1)}:{m.group(2)}" if int(m.group(2)) < 60 else m.group(0),
        s,
    )

    # Deteksi apakah input mengandung jam/waktu spesifik
    has_time = bool(re.search(r'\d{1,2}:\d{2}|\bjam\b|\bpukul\b', s, re.IGNORECASE))

    # ── Normalisasi 2: hapus kata "jam"/"pukul" sebelum waktu ────────────────
    # "hari ini jam 10:47" → "hari ini 10:47"  (dateparser gagal parse jika ada kata "jam")
    # "besok pukul 14:30" → "besok 14:30"
    s_parsed = re.sub(r'\b(jam|pukul)\s+', '', s, flags=re.IGNORECASE)

    dt = dateparser.parse(
        s_parsed,
        languages=["id", "en"],
        settings={
            "PREFER_DATES_FROM": "future",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "Asia/Jakarta",
        },
    )

    if dt is None:
        return None

    # Konversi ke WIB untuk manipulasi jam
    dt_wib = dt.astimezone(_WIB)

    if not has_time:
        # Tanpa jam spesifik → default jam 09:00 WIB
        dt_wib = dt_wib.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        # Ada jam → tepat di menit yang diminta, nol-kan detik agar tidak drift
        dt_wib = dt_wib.replace(second=0, microsecond=0)

    return dt_wib

from firebase_admin import firestore

# --- Fungsi Parsing Tanggal Lama (jika masih ingin gunakan format lama) ---
def _parse_date(s: str) -> datetime:
    """
    Terima format tanggal:
      - '2025-11-07' (YYYY-MM-DD)
      - '07 November 2025' (DD Month YYYY, Indonesia)
      - ISO bebas (fallback)
    Return: datetime UTC (timezone-aware) agar Firestore happy.
    """
    for fmt in ("%Y-%m-%d", "%d %B %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        raise ValueError("Format due_date tidak dikenali. Pakai 'YYYY-MM-DD' atau 'DD November YYYY'.")

class FirestoreRepo:
    def __init__(self, user_id: str):
        self.db = firestore.client()
        self.uid = user_id

    # ---- PROJECTS ----
    def ensure_project(self, name: str) -> str:
        if not name:
            return None
        col = self.db.collection("users").document(self.uid).collection("projects")
        q = col.where("name_lower", "==", name.lower()).limit(1).stream()
        for doc in q:
            return doc.id
        ref = col.document()
        ref.set({
            "name": name.title(),
            "name_lower": name.lower(),
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        return ref.id

    # ---- TASKS ----
    def create_task(self, description: str, due_date: str | None, project_name: str | None):
        proj_id = self.ensure_project(project_name) if project_name else None
        data = {
            "description": description,
            "status": "belum selesai",
            "project_id": proj_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
        if due_date:
            # Menggunakan parsing tanggal dengan dateparser
            dt = parse_due_date_any(due_date)  # Parsing otomatis
            if not dt:
                raise ValueError("Format due_date tidak dikenali. Pakai 'YYYY-MM-DD' atau 'DD November YYYY'.")
            data["due_date"] = dt  # Menyimpan datetime
            data["due_date_str"] = dt.strftime("%Y-%m-%d")  # Opsional, simpan juga format string

        self.db.collection("users").document(self.uid).collection("tasks").add(data)
        return True

    def list_all_tasks(self):
        projects_col = self.db.collection("users").document(self.uid).collection("projects").stream()
        project_map = {p.id: p.to_dict().get("name") for p in projects_col}

        tasks_col = self.db.collection("users").document(self.uid).collection("tasks").stream()
        
        result = []
        for d in tasks_col:
            task_data = d.to_dict()
            task_data["id"] = d.id
            if "project_id" in task_data and task_data["project_id"] in project_map:
                task_data["project_name"] = project_map[task_data["project_id"]]
            else:
                task_data["project_name"] = None
            result.append(task_data)
        return result

    def list_active_tasks(self):
        projects_col = self.db.collection("users").document(self.uid).collection("projects").stream()
        project_map = {p.id: p.to_dict().get("name") for p in projects_col}
        
        tasks_col = self.db.collection("users").document(self.uid).collection("tasks").where("status", "==", "belum selesai").stream()
        
        result = []
        for d in tasks_col:
            task_data = d.to_dict()
            task_data["id"] = d.id
            if "project_id" in task_data and task_data["project_id"] in project_map:
                task_data["project_name"] = project_map[task_data["project_id"]]
            else:
                task_data["project_name"] = None
            result.append(task_data)
        return result

    def update_status_like(self, target_substr: str, status: str):
        col = self.db.collection("users").document(self.uid).collection("tasks")
        ok = False
        for doc in col.stream():
            if target_substr.lower() in doc.to_dict().get("description", "").lower():
                doc.reference.update({"status": status, "updated_at": firestore.SERVER_TIMESTAMP})
                ok = True
        return ok

    def edit_task_like(self, target_substr: str, changes: dict):
        col = self.db.collection("users").document(self.uid).collection("tasks")
        changed = False
        for doc in col.stream():
            d = doc.to_dict()
            if target_substr.lower() in d.get("description", "").lower():
                payload = {"updated_at": firestore.SERVER_TIMESTAMP}
                if changes.get("description"):
                    payload["description"] = changes["description"]
                if changes.get("due_date"):
                    # Menggunakan parsing tanggal dengan dateparser
                    dt = parse_due_date_any(changes["due_date"])  # Parsing otomatis
                    if dt:
                        payload["due_date"] = dt
                        payload["due_date_str"] = dt.strftime("%Y-%m-%d")  # Simpan juga string
                if changes.get("project_name"):
                    payload["project_id"] = self.ensure_project(changes["project_name"])
                doc.reference.update(payload)
                changed = True
        if not changed:
            raise ValueError("Task yang dituju tidak ditemukan untuk di-edit.")
        return changed

    def delete_task_like(self, target_substr: str):
        col = self.db.collection("users").document(self.uid).collection("tasks")
        deleted = False
        for doc in col.stream():
            if target_substr.lower() in doc.to_dict().get("description", "").lower():
                doc.reference.delete()
                deleted = True
        return deleted

    def list_projects(self):
        projects_col = self.db.collection("users").document(self.uid).collection("projects").stream()
        tasks_col_ref = self.db.collection("users").document(self.uid).collection("tasks")
        
        result = []
        for p in projects_col:
            project_data = p.to_dict()
            project_data["id"] = p.id
            
            # Run a count query for tasks associated with this project
            # This is an efficient way to count documents without fetching them all
            count_query = tasks_col_ref.where("project_id", "==", p.id).count()
            
            # The result of a count query is a list of lists, e.g., [[value=5]]
            count_result = count_query.get()
            task_count = count_result[0][0].value if count_result else 0
            
            project_data["task_count"] = task_count
            result.append(project_data)
            
        return result
