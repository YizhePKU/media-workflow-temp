根据一些预定义的方面，从图像中提取详细描述。输出应为简体中文。

输出应为一个包含以下键的JSON对象：
- usage （用途）
- mood （情绪）
- color_scheme （配色方案）
- culture_traits （文化特征）
- industry_domain （行业领域）
- seasonality （季节性）
- holiday_theme （节日主题）

每个值应为用简体中文描述图像的完整且详细的长句。如果无法从图像中提取相关信息，或者结果模糊，请将值设置为 null。
