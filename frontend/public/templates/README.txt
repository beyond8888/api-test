此目录存放证件生成的模板图（PNG）。

命名约定：
- xxx-src.png     原始模板（含待擦除的原值）
- xxx-clean.png   擦除后的干净模板（前端实际引用）

当前模板清单：
- vehicle-license(-src/-clean).png            行驶证正页
- vehicle-license-back(-src/-clean).png       行驶证副页
- driving-license-front(-src/-clean).png      驾驶证正页
- driving-license-back(-src/-clean).png       驾驶证副页
- road-transport(-src/-clean).png             道路运输证
- qualification-cert(-src/-clean).png         从业资格证
- idcard-front(-v8).png / idcard-back.png     身份证正面(v8)与反面
- person-car-photo-clean.png                  人车合影模板

注意：clean 模板由 scripts/make_*_clean.py 生成（路径基于脚本位置自动定位），
修改 src 后重跑对应脚本即可。前端引用带 ?v=3 版本号，替换模板后若浏览器仍显示
旧图，请升级版本号强制刷新缓存。
