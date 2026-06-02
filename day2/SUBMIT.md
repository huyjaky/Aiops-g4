## plot template count time series, anomaly highlighted
<img width="1489" height="1189" alt="image" src="https://github.com/user-attachments/assets/eb4a7546-cac0-4a15-bbb3-698f701c7c87" />

## output Drain3 (số template, top-10), tuning log (sim_th values + kết quả)

### số template, tuning log (sim_th values + kết quả)
```
Ground Truth unique templates count: 120
Similarity Threshold: 0.1 -> Generated 120 templates
Similarity Threshold: 0.3 -> Generated 120 templates
Similarity Threshold: 0.5 -> Generated 120 templates
Similarity Threshold: 0.7 -> Generated 466 templates

Best similarity threshold: 0.1 (produces 120 templates, closest to 120)
```

## top-10
<img width="1409" height="378" alt="image" src="https://github.com/user-attachments/assets/8aa49732-7630-4843-9d22-af2b0e5aff1f" />

## Evaluation on Window-level Anomaly Detection
```
              precision    recall  f1-score   support

         0.0       0.90      0.91      0.91       736
         1.0       0.22      0.19      0.20        95

    accuracy                           0.83       831
   macro avg       0.56      0.55      0.56       831
weighted avg       0.82      0.83      0.83       831
```

## Find Template Clusters
```
--- Template Clusters ---

Cluster 0:
  - instruction cache parity error corrected
  - CE sym <*>, at <*>, mask <*>
  - ciod: failed to read message prefix on control stream (CioStream socket to <*>.<*>.<*>.<*>
  ... (total 74 templates)

Cluster 1:
  - force load/store alignment...............<*>
  - data TLB error interrupt
  - data storage interrupt
  ... (total 13 templates)

Cluster 2:
  - <*> ddr errors(s) detected and corrected on rank <*>, symbol <*>, bit <*>
  - total of <*> ddr error(s) detected and corrected
  - <*> torus receiver z+ input pipe error(s) (dcr <*>) detected and corrected
  ... (total 12 templates)

Cluster 3:
  - data address: <*>
  - data address: <*>
  - data address: <*>
  ... (total 10 templates)

Cluster 4:
  - critical input interrupt enable...<*>
  - suppressing further interrupts of same type
  - critical input interrupt (unit=<*> bit=<*>): warning for torus y+ wire
  ... (total 7 templates)

Cluster 5:
  - <*> <*> alignment exceptions
  - <*> <*> alignment exceptions
  - <*> <*> alignment exceptions
  ... (total 109 templates)

Cluster 6:
  - ciod: LOGIN <*> failed: No such file or directory
  - ciod: Error loading /home/draeger/<*>: invalid or missing program image, No such file or directory
  - ciod: Error loading ./runtime_malloc: invalid or missing program image, No such file or directory
  ... (total 7 templates)

Cluster 7:
  - iar <*> dear <*>
  - iar <*> dear <*>
  - iar <*> dear <*>
  ... (total 209 templates)

Cluster 8:
  - Ido chip status changed: <*> ip=<*>.<*>.<*>.<*> v=<*> t=<*> status=M Fri Jul <*> <*> PDT <*>
  - Ido chip status changed: <*> ip=<*>.<*>.<*>.<*> v=<*> t=<*> status=M Thu Aug <*> <*> PDT <*>
  - Ido chip status changed: <*> ip=<*>.<*>.<*>.<*> v=<*> t=<*> status=M Tue Aug <*> <*> PDT <*>
  ... (total 4 templates)

Cluster 9:
  - instruction address: <*>
  - instruction address: <*>
  - instruction address: <*>
  ... (total 21 templates)
```
