# Test Plan

```bash
python -m pytest -q
```

## Functions ที่ต้อง Test
1. BookingService.create_booking()
   - ห้องว่าง → booking confirmed
   - ห้องไม่ว่าง → RoomNotAvailableError
   - เวลาซ้อนทับ → ConflictError
   - user ไม่ exists → UserNotFoundError
   - จองย้อนหลัง → InvalidTimeRangeError

2. BookingService.cancel_booking()
   - booking exists และเป็นของ user → cancelled
   - booking ของคนอื่น → ForbiddenError
   - booking ไม่ exists → NotFoundError

## กฎที่ยังไม่มี test (ยอมรับไว้ชั่วคราว)
- [กฎ] — เหตุผลที่ยังไม่ทำ + จะทำเมื่อไหร่


## Fidelity Check (WS-03)
- ลบกฎ: จองย้อนหลัง [booking_start < current] 
- Test ที่แดง: [test_create_booking_raises_invalid_time_range_error_when_booking_in_past - Failed: DID NOT RAISE InvalidTimeRangeError]  ✅ harness ปกป้องกฎนี้

