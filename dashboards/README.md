# Kibana Demo Dashboard

Dashboard cho phần demo dữ liệu thật được tạo bằng lệnh nội bộ trên VPS:

```bash
python3 scripts/init_kibana_saved_objects.py \
  --kibana-url http://108.61.246.243:15601 \
  --display-url http://108.61.246.243:15601
```

Khi chạy `./scripts/k8s-expose.sh`, script này cũng được gọi tự động sau khi Kibana
port-forward sẵn sàng.

Dashboard chính:

- `Vietnam Public Trend Intelligence`
- URL demo public: `http://108.61.246.243:15601/app/dashboards#/view/sma-vietnam-public-trend-intelligence`

Các object được seed:

- Data views: `public_content_events`, `public_trend_metrics`,
  `public_trend_alerts`
- Vega charts: content volume, top trending topics, trend mention timeline,
  source distribution, alert topics by score
- Discover tables: latest trend alerts, representative content events
