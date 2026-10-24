Endpoint `/chat` tidak menggunakan body JSON. Anda cukup memberikan pesan dalam bentuk string biasa.

Berikut adalah beberapa contoh pesan yang bisa Anda coba di Swagger UI untuk mengetes fungsionalitas AI:

### 1. Membuat Tugas Baru
```
buatkan tugas baru: belajar FastAPI besok jam 3 sore
```

### 2. Melihat Daftar Tugas
```
ada tugas apa aja yang belum selesai?
```
atau
```
lihat semua tugasku
```

### 3. Memperbarui Status Tugas
```
tandai 'belajar FastAPI' sebagai selesai
```

### 4. Menghapus Tugas
```
hapus tugas 'belajar FastAPI'
```

### 5. Mengedit Tugas
```
edit tugas 'belajar FastAPI' jadi 'mastering FastAPI'
```

Salin-tempel salah satu kalimat di atas ke dalam field `user_message` di Swagger UI untuk melihat respons dari AI.
