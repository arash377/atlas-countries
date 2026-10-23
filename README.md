# محتوای کشورها — اطلس

محتوای عمومی اپ اندروید اطلس؛ شامل متن‌ها و جدول‌های JSON، عکس‌ها، نقشه و صوت. سورس اپ در مخزن جداگانه [atlas](https://github.com/arash377/atlas) قرار دارد.

## نشانی‌ها

پس از فعال‌سازی Pages و انتشار موفق، نشانی پایهٔ اپ:

`https://arash377.github.io/atlas-countries/`

فهرست کشورها: `data/countries.json`

## فعال‌سازی نخستین انتشار

در Settings → Pages، مقدار Source را GitHub Actions انتخاب کنید. سپس در Actions، گردش کار Publish country content را اجرا کنید. پس از آن، هر push روی main محتوا را خودکار منتشر می‌کند. فقط data، assets، region-map.json و صفحه معرفی منتشر می‌شوند.

## ویرایش محتوا

سندهای ایران در data/countries/IRN هستند. پس از ویرایش هر سند، revision آن را افزایش دهید و revision و byte_length همان بخش را در data/countries.json هماهنگ کنید. برای تغییر فهرست، revision فهرست نیز افزایش می‌یابد. byte_length اندازهٔ دقیق فایل بر حسب بایت UTF-8 است.

continent قاره را مشخص می‌کند و added_order ترتیب اضافه‌شدن کشورهاست؛ کشور جدید عدد بزرگ‌تر می‌گیرد.

مجوز فونت و اعتبار رسانه‌ها در فایل‌های همراه و داده‌ها حفظ شده‌اند.
