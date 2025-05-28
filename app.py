import gspread
import pandas as pd
from google.oauth2 import service_account
import hashlib
import pandas as pd
import os
import json
import numpy as np
import hmac
import calendar
import requests
import streamlit as st
from datetime import datetime,timezone, timedelta


if st.query_params.get("trigger") == "update":
    with st.spinner("Call API", show_time=True):



        def generate_signature(secret_key, timestamp):
            payload = timestamp.encode('utf-8')
            secret_key = secret_key.encode('utf-8')

            hmac_object = hmac.new(secret_key, payload, hashlib.sha256)
            
            return hmac_object.hexdigest()

        api_token = "aat.NTA.eyJ2IjoxLCJ1Ijo4MTk2MTksImQiOjEyMjU0NDUsImFpIjo1NTA3NCwiYWsiOiJjMDU1MTNjZS02ZWJlLTRmZTAtYWQwNC00MGQ1NDQ1OWZmMDEiLCJhbiI6IktyaXN0YWwgQXV0b21hdGlvbiIsImFwIjoiNjQ5YTUyZGItOGY3Ni00NGQyLThmMGQtZGU2MDIwMDUwZGI4IiwidCI6MTc0NDc4MDU0NzcxMH0.QeoDo2DCNvI0V/fVQT2IQP8I6v69GOVMRRjSznGkLXdysVtbR9ZTky2FO45cFgVfwWPlLeeSpYXQrICLExUB0MYzX+BqgtXmm/Eb7vc+lRssKuhUbUdpYomW3WXLQSBUJeiPr5KT1wxaIBOk2PIBH09JqdY5yD94rG56xvy9urlr8km0HbtFeVlf8ScL6zFE/jJv4Nu+njY=.0xJjBtaQRlBRfXntN6r+aITBX6BFwvMLz5IK+eDUrpY"
        signature_secret = "EjESUUVVTg5XYDUF9uzMB3PqgEH2G2Sj4OY54GA3k0QFTkb9J5hktE40RM1heIsf"

        # Menambahkan host base URL
        host = "https://zeus.accurate.id"

        def url(endpoint):
            host = "https://zeus.accurate.id"
            url = f"{host}{endpoint}"

            # Format timestamp sesuai standar Accurate (contoh: ISO 8601 UTC)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # Format UTC

            # Pastikan signature di-generate dengan timestamp yang sama
            signature = generate_signature(signature_secret, timestamp)  # Asumsi fungsi ini sudah benar

            headers = {
                "Authorization": f"Bearer {api_token}",
                "X-Api-Timestamp": timestamp,  # Format harus sama dengan yang digunakan di signature
                "X-Api-Signature": signature,
                "X-Language-Profile": "US"
            }
            


            response = requests.get(url, headers=headers)
            return response.json()  # Handle error jika response.status_code != 200

        google_cloud_secrets = st.secrets["google_cloud"]
        creds = service_account.Credentials.from_service_account_info(
            google_cloud_secrets,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)


        def get_data_gsheet(spreadsheet_id, sheetname,range):
            # Mengambil semua data dari worksheet
            all_data = client.open_by_key(spreadsheet_id).worksheet(sheetname).get(range)
            
            # Memisahkan header (baris pertama) dan data
            headers = all_data[0]  # Baris pertama sebagai header
            rows = all_data[1:]    # Baris berikutnya sebagai data
            
            # Mengubah list of lists menjadi list of dictionaries dengan header sebagai key
            data = [dict(zip(headers, row)) for row in rows]
            
            return data


        def update_data(spreadsheet_id, sheetname, df):
            # Buka worksheet
            
            sh = client.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(sheetname)

            # Hapus semua isi worksheet
            worksheet.clear()

            # Siapkan header + data
            data = [df.columns.tolist()] + df.values.tolist()

            # Bersihin NaN supaya tidak error waktu update
            data = [[cell if pd.notna(cell) else "" for cell in row] for row in data]

            # Update semua data ke sheet
            worksheet.update('A1', data,value_input_option='USER_ENTERED')
        def get_all_listdo(endpoint):
            page = 1
            all_data = []
            while True:



                data = url(f"{endpoint}&sp.page={page}")

                datas = data.get('d', [])

                if not datas:
                    print(f"✅ Halaman {page} kosong, selesai.")
                    break

                all_data.extend(datas)
                page += 1

            return all_data
        def ambil_detail_journal(data):
            hasil = []
            for item in data:
                journal_id = item['id']
                detail = url(f"/accurate/api/journal-voucher/detail.do?id={journal_id}")

                for line in detail.get('d', {}).get('detailJournalVoucher', []):
                    hasil.append({
                        'id': journal_id,
                        'date': item['transDate'],
                        'type': line.get('amountType'),
                        'akun': line.get('glAccount', {}).get('name'),
                        'nilai': line.get('amount'),
                        'description':line.get('description'),
                        'memo':line.get('memo')
                    })

            return hasil
        
    with st.spinner("Mengambil Data terupdate", show_time=True):
        today = datetime.today()
        first_date = today - timedelta(days=14)
        first_date = first_date.strftime("%d/%m/%Y")
        last_date = today.strftime("%d/%m/%Y")


        print(first_date)
        print(last_date)
        filtered_check = get_all_listdo(f"/accurate/api/journal-voucher/list.do?filter.transDate.op=BETWEEN&filter.transDate.val[0]={first_date}&filter.transDate.val[1]={last_date}&fields=id,transDate&sp.pageSize=1000000")
        update_journal = ambil_detail_journal(filtered_check)
        
    with st.spinner("Gabung Data...", show_time=True):
        df_all_detail = pd.DataFrame(get_data_gsheet("1cjR6k-OCWmeSfCRS_3b9B3wgQc8a-d_pIvWzcZpz1Uw", "JSON", "A:H"))
        df_all_detail['date'] = pd.to_datetime(df_all_detail['date'])
        df_all_detail['nilai'] = pd.to_numeric(df_all_detail['nilai'])
        df_update_journal = pd.DataFrame(update_journal)
        df_update_journal['date'] = pd.to_datetime(df_update_journal['date'])
        min_date = df_update_journal['date'].min()
        max_date = df_update_journal['date'].max()
        result = df_all_detail[
            (df_all_detail['date'] < min_date) | (df_all_detail['date'] > max_date)
        ]
        result = pd.concat([result, df_update_journal], ignore_index=True)
        for_json = result.copy()
        for_json['date'] = for_json['date'].dt.strftime('%-m/%-d/%Y')
        update_data("1cjR6k-OCWmeSfCRS_3b9B3wgQc8a-d_pIvWzcZpz1Uw","JSON",for_json)
        result['Debit'] = result.apply(lambda x: x['nilai'] if x['type'] == 'DEBIT' else 0, axis=1)
        result['Credit'] = result.apply(lambda x: x['nilai'] if x['type'] == 'CREDIT' else 0, axis=1)
        
    with st.spinner("Update Data ke Google Sheet", show_time=True):
        final_google = result[result['akun'].str.contains("Driver")]
        final_google = final_google.sort_values('date')
        final_google['Balance'] = (final_google['Debit'] - final_google['Credit']).cumsum()

        final_google['Saldo'] = np.where(final_google['Debit'] == 0, final_google['Credit'] * -1, 
                                                np.where(final_google['Credit'] == 0, final_google['Debit'], np.nan))

        # Fill NaN values if needed (optional)
        final_google['Saldo'] = final_google['Saldo'].fillna(0)
        final_google['Driver Name'] = final_google['akun'].str.replace('Driver - ', '', regex=False)
        final_google['date'] = final_google['date'].dt.strftime('%m/%d/%Y')
        final_google = final_google[['akun', 'Driver Name', 'date', 'memo', 'Debit', 'Credit', 'Balance', 'Saldo']]
        final_google = final_google.fillna("")
        final_google.rename(columns={'Credit': 'Kredit', 'akun':'Nama Perkiraan', 'date':'Tanggal', 'memo': 'Deskripsi'}, inplace=True)
        update_data("1cjR6k-OCWmeSfCRS_3b9B3wgQc8a-d_pIvWzcZpz1Uw","Valentio",final_google)
        st.success("Berhasil Update!!!")
        


if st.button("Update Data"):
    with st.spinner("Call API", show_time=True):



        def generate_signature(secret_key, timestamp):
            payload = timestamp.encode('utf-8')
            secret_key = secret_key.encode('utf-8')

            hmac_object = hmac.new(secret_key, payload, hashlib.sha256)
            
            return hmac_object.hexdigest()

        api_token = "aat.NTA.eyJ2IjoxLCJ1Ijo4MTk2MTksImQiOjEyMjU0NDUsImFpIjo1NTA3NCwiYWsiOiJjMDU1MTNjZS02ZWJlLTRmZTAtYWQwNC00MGQ1NDQ1OWZmMDEiLCJhbiI6IktyaXN0YWwgQXV0b21hdGlvbiIsImFwIjoiNjQ5YTUyZGItOGY3Ni00NGQyLThmMGQtZGU2MDIwMDUwZGI4IiwidCI6MTc0NDc4MDU0NzcxMH0.QeoDo2DCNvI0V/fVQT2IQP8I6v69GOVMRRjSznGkLXdysVtbR9ZTky2FO45cFgVfwWPlLeeSpYXQrICLExUB0MYzX+BqgtXmm/Eb7vc+lRssKuhUbUdpYomW3WXLQSBUJeiPr5KT1wxaIBOk2PIBH09JqdY5yD94rG56xvy9urlr8km0HbtFeVlf8ScL6zFE/jJv4Nu+njY=.0xJjBtaQRlBRfXntN6r+aITBX6BFwvMLz5IK+eDUrpY"
        signature_secret = "EjESUUVVTg5XYDUF9uzMB3PqgEH2G2Sj4OY54GA3k0QFTkb9J5hktE40RM1heIsf"

        # Menambahkan host base URL
        host = "https://zeus.accurate.id"

        def url(endpoint):
            host = "https://zeus.accurate.id"
            url = f"{host}{endpoint}"

            # Format timestamp sesuai standar Accurate (contoh: ISO 8601 UTC)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # Format UTC

            # Pastikan signature di-generate dengan timestamp yang sama
            signature = generate_signature(signature_secret, timestamp)  # Asumsi fungsi ini sudah benar

            headers = {
                "Authorization": f"Bearer {api_token}",
                "X-Api-Timestamp": timestamp,  # Format harus sama dengan yang digunakan di signature
                "X-Api-Signature": signature,
                "X-Language-Profile": "US"
            }
            


            response = requests.get(url, headers=headers)
            return response.json()  # Handle error jika response.status_code != 200

        google_cloud_secrets = st.secrets["google_cloud"]
        creds = service_account.Credentials.from_service_account_info(
            google_cloud_secrets,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)


        def get_data_gsheet(spreadsheet_id, sheetname,range):
            # Mengambil semua data dari worksheet
            all_data = client.open_by_key(spreadsheet_id).worksheet(sheetname).get(range)
            
            # Memisahkan header (baris pertama) dan data
            headers = all_data[0]  # Baris pertama sebagai header
            rows = all_data[1:]    # Baris berikutnya sebagai data
            
            # Mengubah list of lists menjadi list of dictionaries dengan header sebagai key
            data = [dict(zip(headers, row)) for row in rows]
            
            return data


        def update_data(spreadsheet_id, sheetname, df):
            # Buka worksheet
            
            sh = client.open_by_key(spreadsheet_id)
            worksheet = sh.worksheet(sheetname)

            # Hapus semua isi worksheet
            worksheet.clear()

            # Siapkan header + data
            data = [df.columns.tolist()] + df.values.tolist()

            # Bersihin NaN supaya tidak error waktu update
            data = [[cell if pd.notna(cell) else "" for cell in row] for row in data]

            # Update semua data ke sheet
            worksheet.update('A1', data,value_input_option='USER_ENTERED')
        def get_all_listdo(endpoint):
            page = 1
            all_data = []
            while True:



                data = url(f"{endpoint}&sp.page={page}")

                datas = data.get('d', [])

                if not datas:
                    print(f"✅ Halaman {page} kosong, selesai.")
                    break

                all_data.extend(datas)
                page += 1

            return all_data
        def ambil_detail_journal(data):
            hasil = []
            for item in data:
                journal_id = item['id']
                detail = url(f"/accurate/api/journal-voucher/detail.do?id={journal_id}")

                for line in detail.get('d', {}).get('detailJournalVoucher', []):
                    hasil.append({
                        'id': journal_id,
                        'date': item['transDate'],
                        'type': line.get('amountType'),
                        'akun': line.get('glAccount', {}).get('name'),
                        'nilai': line.get('amount'),
                        'description':line.get('description'),
                        'memo':line.get('memo')
                    })

            return hasil
        
    with st.spinner("Mengambil Data terupdate", show_time=True):
        today = datetime.today()
        first_date = today - timedelta(days=14)
        first_date = first_date.strftime("%d/%m/%Y")
        last_date = today.strftime("%d/%m/%Y")


        print(first_date)
        print(last_date)
        filtered_check = get_all_listdo(f"/accurate/api/journal-voucher/list.do?filter.transDate.op=BETWEEN&filter.transDate.val[0]={first_date}&filter.transDate.val[1]={last_date}&fields=id,transDate&sp.pageSize=1000000")
        update_journal = ambil_detail_journal(filtered_check)
        
    with st.spinner("Gabung Data...", show_time=True):
        df_all_detail = pd.DataFrame(get_data_gsheet("1cjR6k-OCWmeSfCRS_3b9B3wgQc8a-d_pIvWzcZpz1Uw", "JSON", "A:H"))
        df_all_detail['date'] = pd.to_datetime(df_all_detail['date'])
        df_all_detail['nilai'] = pd.to_numeric(df_all_detail['nilai'])
        df_update_journal = pd.DataFrame(update_journal)
        df_update_journal['date'] = pd.to_datetime(df_update_journal['date'])
        min_date = df_update_journal['date'].min()
        max_date = df_update_journal['date'].max()
        result = df_all_detail[
            (df_all_detail['date'] < min_date) | (df_all_detail['date'] > max_date)
        ]
        result = pd.concat([result, df_update_journal], ignore_index=True)
        for_json = result.copy()
        for_json['date'] = for_json['date'].dt.strftime('%-m/%-d/%Y')
        update_data("1cjR6k-OCWmeSfCRS_3b9B3wgQc8a-d_pIvWzcZpz1Uw","JSON",for_json)
        result['Debit'] = result.apply(lambda x: x['nilai'] if x['type'] == 'DEBIT' else 0, axis=1)
        result['Credit'] = result.apply(lambda x: x['nilai'] if x['type'] == 'CREDIT' else 0, axis=1)
        
    with st.spinner("Update Data ke Google Sheet", show_time=True):
        final_google = result[result['akun'].str.contains("Driver")]
        final_google = final_google.sort_values('date')
        final_google['Balance'] = (
        final_google['Debit'] - final_google['Credit']  # pakai 'Kredit' jika sudah rename
    ).groupby(final_google['akun']).cumsum()

        final_google['Saldo'] = np.where(final_google['Debit'] == 0, final_google['Credit'] * -1, 
                                                np.where(final_google['Credit'] == 0, final_google['Debit'], np.nan))

        # Fill NaN values if needed (optional)
        final_google['Saldo'] = final_google['Saldo'].fillna(0)
        final_google['Driver Name'] = final_google['akun'].str.replace('Driver - ', '', regex=False)
        final_google['date'] = final_google['date'].dt.strftime('%m/%d/%Y')
        final_google = final_google[['akun', 'Driver Name', 'date', 'memo', 'Debit', 'Credit', 'Balance', 'Saldo']]
        final_google = final_google.fillna("")
        final_google.rename(columns={'Credit': 'Kredit', 'akun':'Nama Perkiraan', 'date':'Tanggal', 'memo': 'Deskripsi'}, inplace=True)
        update_data("1cjR6k-OCWmeSfCRS_3b9B3wgQc8a-d_pIvWzcZpz1Uw","Valentio",final_google)
        st.success("Berhasil Update!!!")
        
        
    
    
        
            
