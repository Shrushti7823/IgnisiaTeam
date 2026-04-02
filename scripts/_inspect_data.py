import pandas as pd
import json

# Inspect fraud_oracle.csv
df = pd.read_csv('datasets/fraud_oracle.csv')
info = {
    "rows": len(df),
    "columns": df.columns.tolist(),
    "fraud_counts": df['FraudFound_P'].value_counts().to_dict(),
    "dtypes": {c: str(df[c].dtype) for c in df.columns},
    "sample_values": {c: [str(v) for v in df[c].unique()[:6]] for c in df.columns},
}
with open('scripts/_data_info.json', 'w') as f:
    json.dump(info, f, indent=2)
print("Done - wrote scripts/_data_info.json")

# Also inspect insurance_claims.csv
df2 = pd.read_csv('datasets/insurance_claims.csv')
info2 = {
    "rows": len(df2),
    "columns": df2.columns.tolist(),
    "fraud_counts": df2['fraud_reported'].value_counts().to_dict(),
    "sample": df2.head(2).to_dict(),
}
with open('scripts/_data_info2.json', 'w') as f:
    json.dump(info2, f, indent=2)
print("Done - wrote scripts/_data_info2.json")
