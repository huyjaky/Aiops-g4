## plot kết quả anomaly detection (2 detector)

## Nếu ưu tiên độ an toàn và hi sinh độ chính xác 
<img width="1587" height="1187" alt="image" src="https://github.com/user-attachments/assets/52d0f4cf-d31c-4883-8345-5844b2cacd24" />

## Nếu ưu tiên độ chính xác trong dự đoán 
<img width="1587" height="1187" alt="image" src="https://github.com/user-attachments/assets/0e293e0b-1586-49db-b8d7-edc9277c603b" />

## bảng so sánh precision/recall

### STL + 3 $\sigma$
```bash
Threshold: 2.0 | Precision: 0.1277 | Recall: 0.0888 | F1 Score: 0.1048
Threshold: 2.5 | Precision: 0.1500 | Recall: 0.0691 | F1 Score: 0.0946
Threshold: 3.0 | Precision: 0.1484 | Recall: 0.0444 | F1 Score: 0.0684
Threshold: 3.5 | Precision: 0.1261 | Recall: 0.0247 | F1 Score: 0.0413
Threshold: 4.0 | Precision: 0.1500 | Recall: 0.0197 | F1 Score: 0.0349
Threshold: 4.5 | Precision: 0.1538 | Recall: 0.0132 | F1 Score: 0.0242
Threshold: 5.0 | Precision: 0.0625 | Recall: 0.0033 | F1 Score: 0.0063
```

---

### Isolation Forest
#### window=48
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Contamination</th>
      <th>Precision</th>
      <th>Recall</th>
      <th>F1 Score</th>
      <th>Pred Anomaly Count</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>0.01</td>
      <td>0.890411</td>
      <td>0.106908</td>
      <td>0.190896</td>
      <td>73</td>
    </tr>
    <tr>
      <th>1</th>
      <td>0.02</td>
      <td>0.662069</td>
      <td>0.157895</td>
      <td>0.254980</td>
      <td>145</td>
    </tr>
    <tr>
      <th>2</th>
      <td>0.03</td>
      <td>0.539171</td>
      <td>0.192434</td>
      <td>0.283636</td>
      <td>217</td>
    </tr>
    <tr>
      <th>3</th>
      <td>0.05</td>
      <td>0.426593</td>
      <td>0.253289</td>
      <td>0.317853</td>
      <td>361</td>
    </tr>
  </tbody>
</table>
</div>

#### window=24
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Contamination</th>
      <th>Precision</th>
      <th>Recall</th>
      <th>F1 Score</th>
      <th>Pred Anomaly Count</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>0.01</td>
      <td>0.780822</td>
      <td>0.093750</td>
      <td>0.167401</td>
      <td>73</td>
    </tr>
    <tr>
      <th>1</th>
      <td>0.02</td>
      <td>0.620690</td>
      <td>0.148026</td>
      <td>0.239044</td>
      <td>145</td>
    </tr>
    <tr>
      <th>2</th>
      <td>0.03</td>
      <td>0.490826</td>
      <td>0.175987</td>
      <td>0.259080</td>
      <td>218</td>
    </tr>
    <tr>
      <th>3</th>
      <td>0.05</td>
      <td>0.385675</td>
      <td>0.230263</td>
      <td>0.288363</td>
      <td>363</td>
    </tr>
  </tbody>
</table>
</div>

## kết luận

| **No** | **Dataset**                              | **Stationarity** | **Seasonality** | **Skewness**                             
| ------ | ---------------------------------------- | ---------------- | --------------- | ---------------------------------------- 
| **1**  | **ambient_temperature_system_failure**   | Yes              | Yes             | Slightly left-skewed - Close to Gaussian | 

- Dữ liệu: Em xác định đây là chuỗi thời gian đơn biến về nhiệt độ, có tính dừng và chu kỳ 24h rõ rệt.
- Phương pháp: Em chọn STL + 3σ để phân tách chu kỳ đơn biến và Isolation Forest để học các đặc trưng đa chiều.
- Kết quả: Em đánh giá Isolation Forest tốt hơn nhờ F1-score (0.2884) và Recall (23.03%) vượt trội so với STL.
- Trade-off: Em nhận thấy khi tăng contamination để tăng Recall (giảm sót lỗi) thì Precision sẽ bị giảm (tăng cảnh báo giả).
- Development choice: Em ưu tiên đưa Isolation Forest (contamination = 0.01) để đo đúng chính xác khi nào hệ thống dừng lại
- Production choice: Em ưu tiên đưa Isolation Forest (contamination = 0.05) vào vận hành thực tế để đảm bảo an toàn tối đa cho hệ thống (đạt độ nhạy cao), chấp nhận một vài cảnh báo giả. 

## Knowledge check 
<img width="2554" height="2174" alt="image" src="https://github.com/user-attachments/assets/eebfceb5-34ba-4f91-9129-77f072b4cd9f" />
<img width="2309" height="3871" alt="image" src="https://github.com/user-attachments/assets/6ced6800-2ec3-422f-b3d4-bfbeee2cb8f5" />
<img width="2382" height="2931" alt="image" src="https://github.com/user-attachments/assets/3491b9ce-4276-4993-b211-5b8073d4fa0b" />
<img width="1793" height="2156" alt="image" src="https://github.com/user-attachments/assets/20a25e06-563a-4ff3-aff0-9ad9b2121395" />
<img width="2274" height="2775" alt="image" src="https://github.com/user-attachments/assets/24efca2c-9e9f-4877-93d5-e2382d667aba" />










