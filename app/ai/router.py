from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime
import json
from typing import Any

from app.core.security import get_current_user_uid
from app.data.repo import FirestoreRepo
from app.core.config import settings

from openai import OpenAI

router = APIRouter(prefix="/chat", tags=["ai"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# =========================
# Helpers
# =========================
def _json_load_maybe(s):
    if s is None:
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s)
    except Exception:
        return {}

def _to_jsonable(obj: Any):
    """Convert Firestore / datetime objects into JSON-serializable structures."""
    # datetime
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Firestore DatetimeWithNanoseconds has isoformat() too
    if hasattr(obj, "isoformat") and callable(getattr(obj, "isoformat")):
        try:
            return obj.isoformat()
        except Exception:
            pass

    # dict
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}

    # list/tuple
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]

    # primitives
    return obj

def _intent_hint(msg: str) -> str:
    m = (msg or "").lower()
    # bantu model biar lebih "ngeh" harus tool
    if any(k in m for k in ["ada tugas", "list tugas", "lihat tugas", "cek tugas", "tugas apa", "tugas gue", "task apa"]):
        return "User wants to LIST tasks."
    if any(k in m for k in ["buat tugas", "tambah tugas", "bikinin tugas", "create task", "buatkan tugas"]):
        return "User wants to CREATE a task."
    if any(k in m for k in ["hapus", "delete"]):
        return "User wants to DELETE a task."
    if any(k in m for k in ["ubah", "edit", "ganti"]):
        return "User wants to EDIT a task."
    if any(k in m for k in ["selesai", "done", "beres"]):
        return "User wants to UPDATE STATUS of a task."
    return ""

# =========================
# Tools (schema BENAR untuk GPT-5 Responses API)
# =========================
TOOLS = [
    {
        "type": "function",
        "name": "list_tasks",
        "description": "Ambil daftar task user dari database. Bisa filter status.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Opsional: 'belum selesai' atau 'selesai'. Kalau kosong, ambil semua."
                }
            },
            "required": []
        }
    },
    {
        "type": "function",
        "name": "create_task",
        "description": "Buat task baru ke database.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Nama/deskripsi task"},
                "due_date": {
                    "type": "string",
                    "description": (
                        "Tanggal + JAM deadline. Contoh: 'besok jam 10:00', '14 November 2025 09:00', '2025-11-14 15:30'. "
                        "SELALU sertakan jam jika user menyebutkannya. "
                        "Jika user tidak menyebut jam, cukup kirim tanggalnya saja (sistem akan default ke 09:00 WIB). "
                        "Opsional."
                    )
                },
                "project_name": {"type": "string", "description": "Nama project (opsional)"}
            },
            "required": ["description"]
        }
    },
    {
        "type": "function",
        "name": "update_status",
        "description": "Ubah status task berdasarkan potongan teks target (mis: 'bab 1').",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Potongan nama/deskripsi task"},
                "status": {"type": "string", "description": "Contoh: 'selesai' atau 'belum selesai'"}
            },
            "required": ["target", "status"]
        }
    },
    {
        "type": "function",
        "name": "edit_task",
        "description": "Edit task berdasarkan potongan teks target (mis: 'bab 1').",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "description": {"type": "string"},
                "due_date": {"type": "string"},
                "project_name": {"type": "string"}
            },
            "required": ["target"]
        }
    },
    {
        "type": "function",
        "name": "delete_task",
        "description": "Hapus task berdasarkan potongan teks target (mis: 'bab 1').",
        "parameters": {
            "type": "object",
            "properties": {
                "target": {"type": "string"}
            },
            "required": ["target"]
        }
    },
]

SYSTEM = (
    "Kamu adalah TaskMaster AI, asisten manajemen tugas.\n"
    f"Tanggal hari ini: {datetime.now():%d %B %Y}. Timezone: WIB (UTC+7).\n\n"
    "ATURAN WAJIB (keras):\n"
    "- Kalau user minta melihat/cek daftar tugas => WAJIB panggil tool `list_tasks`.\n"
    "- Kalau user minta buat/tambah tugas => WAJIB panggil tool `create_task`.\n"
    "- Kalau user minta hapus tugas => WAJIB panggil tool `delete_task`.\n"
    "- Kalau user minta ubah/edit => WAJIB panggil tool `edit_task`.\n"
    "- Kalau user minta tandai selesai/belum selesai => WAJIB panggil tool `update_status`.\n"
    "- Jangan jawab 'ngapain' / basa-basi. Langsung eksekusi tool kalau maksudnya jelas.\n"
    "- Kalau kurang info (misal user bilang 'buat tugas' tapi gak ada judul) => tanya 1 pertanyaan klarifikasi.\n"
    "- Bahasa santai Indonesia.\n\n"
    "ATURAN due_date:\n"
    "- SALIN PERSIS jam yang user sebut, JANGAN ubah atau bulatkan. Contoh: user bilang 'jam 10.47' → kirim 'jam 10:47' (titik jadi titik dua, angka sama persis).\n"
    "- Format due_date: '<hari/tanggal> <jam>', contoh: 'hari ini jam 10:47', 'besok jam 14:30', '2025-11-14 09:00'.\n"
    "- Jika user tidak menyebut jam => kirim tanggalnya saja tanpa jam, sistem akan set default jam 09:00 WIB.\n"
    "- Semua waktu dalam WIB (UTC+7). JANGAN konversi atau ubah.\n"
)

@router.post("")
def handle_chat(request: Request, user_message: str, uid: str = Depends(get_current_user_uid)):
    print("====== HEADERS RECEIVED ON /chat ======")
    print(request.headers)
    print("======================================")
    repo = FirestoreRepo(user_id=uid)

    try:
        # --- Step 1: minta model memutuskan tool apa ---
        input_list = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_message + (("\n\n[Hint] " + _intent_hint(user_message)) if _intent_hint(user_message) else "")},
        ]

        r1 = client.responses.create(
            model=settings.OPENAI_MODEL,  # .env: OPENAI_MODEL=gpt-5
            tools=TOOLS,
            input=input_list,
            tool_choice="auto",
        )

        # Simpan output model ke input_list untuk step berikutnya
        input_list += (r1.output or [])

        # Ambil function calls (di Responses API namanya "function_call")
        calls = [item for item in (r1.output or []) if getattr(item, "type", None) == "function_call"]

        # Kalau model gak manggil tool tapi user jelas ngomong "tugas",
        # paksa minimal list_tasks biar gak jawab ngaco
        if not calls and "tugas" in (user_message or "").lower():
            # paksa jalankan list_tasks
            tasks = repo.list_all_tasks()
            input_list.append({
                "type": "function_call_output",
                "call_id": "forced_list_tasks",
                "output": json.dumps({"tasks": _to_jsonable(tasks)}, ensure_ascii=False)
            })
            # Step 2: minta model jawab pakai hasil DB
            r2 = client.responses.create(
                model=settings.OPENAI_MODEL,
                tools=TOOLS,
                input=input_list,
                instructions="Jawab singkat dan jelas berdasarkan data tasks dari tool output.",
            )
            return {"reply": (r2.output_text or "").strip()}

        # --- Execute each tool call ---
        for item in calls:
            name = item.name
            args = _json_load_maybe(item.arguments)

            if name == "list_tasks":
                status = (args.get("status") or "").strip()
                if status:
                    # kalau repo lu belum punya filter status, fallback manual
                    all_tasks = repo.list_all_tasks()
                    filtered = [t for t in all_tasks if str(t.get("status", "")).lower() == status.lower()]
                    payload = {"tasks": _to_jsonable(filtered)}
                else:
                    payload = {"tasks": _to_jsonable(repo.list_all_tasks())}

                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(payload, ensure_ascii=False)
                })

            elif name == "create_task":
                desc = (args.get("description") or "").strip()
                if not desc:
                    desc = user_message.strip()[:80]

                ok = repo.create_task(desc, args.get("due_date"), args.get("project_name"))
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({"success": bool(ok)}, ensure_ascii=False)
                })

            elif name == "update_status":
                ok = False
                if args.get("target") and args.get("status"):
                    ok = repo.update_status_like(args["target"], args["status"])
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({"success": bool(ok)}, ensure_ascii=False)
                })

            elif name == "edit_task":
                ok = False
                target = args.get("target")
                if target:
                    changes = {k: v for k, v in args.items() if k in ("description", "due_date", "project_name") and v}
                    ok = repo.edit_task_like(target, changes)
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({"success": bool(ok)}, ensure_ascii=False)
                })

            elif name == "delete_task":
                ok = False
                if args.get("target"):
                    ok = repo.delete_task_like(args["target"])
                input_list.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps({"success": bool(ok)}, ensure_ascii=False)
                })

        # --- Step 2: minta model jawab final berdasarkan output tools ---
        r2 = client.responses.create(
            model=settings.OPENAI_MODEL,
            tools=TOOLS,
            input=input_list,
            instructions=(
                "Balas santai, singkat, dan jelas.\n"
                "Kalau success=true, sebutkan apa yang dilakukan.\n"
                "Kalau list_tasks, tampilkan daftar tugas (bullet) dan due_date kalau ada.\n"
            ),
        )

        return {"reply": (r2.output_text or "").strip() or "Sip!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
