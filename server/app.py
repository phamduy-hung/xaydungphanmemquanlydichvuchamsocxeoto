"""
Flask API Server — Hệ thống nhận đặt lịch từ web
Chạy: python3 server/app.py
Port: 5000
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# ──────────────────────────────────────────────
# Khởi tạo Flask app
# ──────────────────────────────────────────────
app = Flask(__name__)
CORS(app)  # Cho phép web frontend (localhost:5173) gọi API này

DB_PATH = Path(__file__).resolve().parent / "bookings.db"


# ──────────────────────────────────────────────
# Khởi tạo database SQLite
# ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ho_ten      TEXT NOT NULL,
            sdt         TEXT NOT NULL,
            bien_so     TEXT,
            dich_vu     TEXT,
            ngay_hen    TEXT,
            gio_hen     TEXT,
            ghi_chu     TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────
# API Endpoints
# ──────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now().isoformat()})


@app.route("/api/booking", methods=["POST"])
def create_booking():
    """Khách hàng gửi form đặt lịch từ web."""
    data = request.get_json(silent=True) or {}

    ho_ten  = (data.get("ho_ten") or "").strip()
    sdt     = (data.get("sdt") or "").strip()
    bien_so = (data.get("bien_so") or "").strip()
    dich_vu = (data.get("dich_vu") or "").strip()
    ngay_hen = (data.get("ngay_hen") or "").strip()
    gio_hen  = (data.get("gio_hen") or "").strip()
    ghi_chu  = (data.get("ghi_chu") or "").strip()

    if not ho_ten or not sdt:
        return jsonify({"success": False, "error": "Thiếu Họ tên hoặc Số điện thoại"}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO bookings (ho_ten, sdt, bien_so, dich_vu, ngay_hen, gio_hen, ghi_chu)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ho_ten, sdt, bien_so, dich_vu, ngay_hen, gio_hen, ghi_chu),
        )
        conn.commit()
        booking_id = cursor.lastrowid
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "message": "Đặt lịch thành công! Chúng tôi sẽ liên hệ xác nhận sớm.",
        "booking_id": booking_id,
    }), 201


@app.route("/api/bookings/pending", methods=["GET"])
def get_pending_bookings():
    """Desktop app polling — lấy danh sách đơn chưa xử lý."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM bookings WHERE status = 'pending' ORDER BY created_at DESC"
        ).fetchall()
    finally:
        conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/bookings/all", methods=["GET"])
def get_all_bookings():
    """Lấy tất cả đơn (cho tab lịch sử)."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM bookings ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    finally:
        conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/bookings/<int:booking_id>/accept", methods=["PATCH"])
def accept_booking(booking_id):
    """Nhân viên tiếp nhận đơn."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE bookings SET status = 'accepted' WHERE id = ?", (booking_id,)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"success": False, "error": "Không tìm thấy đơn"}), 404

    return jsonify({"success": True, "booking": dict(row)})


@app.route("/api/bookings/<int:booking_id>/reject", methods=["PATCH"])
def reject_booking(booking_id):
    """Nhân viên từ chối / hủy đơn."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE bookings SET status = 'rejected' WHERE id = ?", (booking_id,)
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"success": True})


@app.route("/api/bookings/count/pending", methods=["GET"])
def count_pending():
    """Đếm số đơn pending — dùng cho badge trên desktop."""
    conn = get_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE status = 'pending'"
        ).fetchone()[0]
    finally:
        conn.close()
    return jsonify({"count": count})


# ──────────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("  🚗 API Server đang chạy tại http://localhost:8765")
    print("  📋 Nhận đặt lịch từ web → chuyển về desktop")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8765, debug=False)
