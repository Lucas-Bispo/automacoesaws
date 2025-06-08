import boto3
import pandas as pd
import logging

def collect_data():
    iam_client = boto3.client('iam')
    logging.info("Coletando dados de IAM (Usuários e Grupos)...")
    
    # Coleta usuários
    users_paginator = iam_client.get_paginator('list_users')
    users_data = []
    for page in users_paginator.paginate():
        for user in page['Users']:
            user['Groups'] = ", ".join([g['GroupName'] for g in iam_client.list_groups_for_user(UserName=user['UserName']).get('Groups', [])])
            users_data.append(user)
    
    # Coleta grupos
    groups_paginator = iam_client.get_paginator('list_groups')
    groups_data = [group for page in groups_paginator.paginate() for group in page['Groups']]
            
    return {
        'IAM_Users': pd.json_normalize(users_data),
        'IAM_Groups': pd.json_normalize(groups_data)
    }