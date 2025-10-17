# AI Translation Setup Guide
**Technical Documentation for Developers**

---

## Implementation Status

### ✅ Phase 1: Django Setup (COMPLETE)

**Database:**
- django-modeltranslation 0.19.0 installed
- Migration 0015: Added `_en` and `_es` fields
- Migration 0016: Spanish→`_es`, Taxonomy EN/ES filled
- Fields: `translation_status`, `translation_source_hash`, `last_translated_at`, `translation_error`

**Translation Strategy:**
- Strain.name, Terpene.name, ArticleCategory.name → NOT translated
- Strain/Article/Terpene content → Translatable
- Taxonomy (Feeling, Flavor, etc.) → Translatable
- Strain.img_alt_text → Translatable

**Admin:**
- Language tabs in forms
- Status badges (Synced/Pending/Outdated/Failed)
- "Force retranslate" action

**Frontend:**
- Django i18n configured (`LANGUAGE_CODE = 'es'`)
- Language switcher (🇬🇧 EN / 🇪🇸 ES)
- Templates with `{% trans %}` tags

**Files:**
- `apps/strains/models.py` - TranslationMixin added
- `apps/strains/translation.py` - All models registered
- `apps/strains/admin.py` - Custom displays
- `locale/en/LC_MESSAGES/django.po` - UI translations
- `Dockerfile` - gettext package added

---

### 📋 Phase 2: Initial Translation (ES→EN) - PENDING

**Current Situation:**
- Spanish content in `_es` fields
- English fields (`_en`) empty
- Need bulk translation before enabling automated workflow

**Plan:**

#### Step 1: Create Management Command

**File:** `apps/strains/management/commands/translate_existing_content.py`

**Features:**
```python
# Direct OpenAI API calls (no SQS, no signals)
# Configurable direction: --direction es-to-en | en-to-es
# Progress bar, pause (1.5s), retry logic
# Resume from interruption
# Detailed logging
```

**Rate Limits:**
- gpt-4o-mini: 500 RPM (Tier 1) / 5000 RPM (Tier 2)
- Pause: 1.5 seconds between requests
- ~500 strains + 50 articles = ~14 minutes

**Usage:**
```bash
# Bulk translate existing Spanish→English
python manage.py translate_existing_content --direction es-to-en

# Dry run
python manage.py translate_existing_content --direction es-to-en --dry-run

# Specific model
python manage.py translate_existing_content --direction es-to-en --model Strain
```

**Implementation (stub):**
```python
from django.core.management.base import BaseCommand
from openai import OpenAI
import time
from apps.strains.models import Strain, Article, Terpene

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--direction', choices=['es-to-en', 'en-to-es'])
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--model', choices=['Strain', 'Article', 'Terpene', 'all'])
        parser.add_argument('--pause', type=float, default=1.5)

    def handle(self, *args, **options):
        # Get OpenAI client
        # Query objects needing translation
        # Loop with progress bar:
        #   - Translate via OpenAI
        #   - Update DB
        #   - Sleep (pause)
        #   - Handle errors
        pass
```

#### Step 2: Execute on Production

1. Deploy Phase 1 to production
2. Run: `translate_existing_content --direction es-to-en`
3. Monitor (~15-20 min)
4. Verify in admin
5. QA check sample translations

#### Step 3: Switch to EN→ES

1. Update Lambda: `SOURCE_LANGUAGE='en'`, `TARGET_LANGUAGE='es'`
2. Update signals to send direction in SQS message
3. Deploy Lambda
4. Test automated workflow

---

### ⏳ Phase 3: AWS Lambda Automation - PENDING

**Architecture:**

```
Admin saves Strain (EN) → pre_save signal (hash check)
                       → post_save signal (needs_translation?)
                       → SQS message {"direction": "en-to-es"}
                       → Lambda triggered
                       → OpenAI API
                       → Update DB (_es fields)
                       → Status: "synced"
```

---

## AWS Infrastructure Setup

### Prerequisites

- AWS account with permissions
- OpenAI API key
- RDS PostgreSQL accessible from Lambda

### 1. IAM Role

**Policy:** `canna-lambda-translation-policy`
```json
{
  "Statement": [
    {"Effect": "Allow", "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], "Resource": "arn:aws:sqs:*:*:canna-translation-queue.fifo"},
    {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:*:*:*"},
    {"Effect": "Allow", "Action": ["secretsmanager:GetSecretValue"], "Resource": ["arn:aws:secretsmanager:*:*:secret:canna/*"]}
  ]
}
```

**Role:** `canna-lambda-translator-role` (attach policy above)

---

### 2. Secrets Manager

**Database Credentials:**
```bash
aws secretsmanager create-secret --name canna/database/credentials --secret-string '{
  "host": "your-db.rds.amazonaws.com",
  "port": "5432",
  "database": "canna_db",
  "username": "lambda_user",
  "password": "SECURE_PASSWORD"
}'
```

**OpenAI API Key:**
```bash
aws secretsmanager create-secret --name canna/openai/api-key --secret-string '{
  "api_key": "sk-proj-XXXXX"
}'
```

**Database User (PostgreSQL):**
```sql
CREATE USER lambda_user WITH PASSWORD 'SECURE_PASSWORD';
GRANT CONNECT ON DATABASE canna_db TO lambda_user;
GRANT SELECT, UPDATE ON strains_strain, strains_article, strains_terpene TO lambda_user;
```

---

### 3. SQS Queues

**Main Queue (FIFO):**
```bash
aws sqs create-queue --queue-name canna-translation-queue.fifo --attributes '{
  "FifoQueue": "true",
  "ContentBasedDeduplication": "true",
  "MessageRetentionPeriod": "1209600",
  "VisibilityTimeout": "300"
}'
```

**Dead Letter Queue:**
```bash
aws sqs create-queue --queue-name canna-translation-dlq.fifo --attributes '{
  "FifoQueue": "true",
  "ContentBasedDeduplication": "true"
}'
```

**Redrive Policy:**
```bash
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT_ID/canna-translation-dlq.fifo --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT_ID/canna-translation-queue.fifo --attributes '{"RedrivePolicy": "{\"deadLetterTargetArn\":\"'$DLQ_ARN'\",\"maxReceiveCount\":\"3\"}"}'
```

---

### 4. Lambda Function

**Configuration:**
- Name: `canna-translator`
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 300 seconds (5 min)
- Role: `canna-lambda-translator-role`

**Environment Variables:**
```bash
AWS_REGION=us-east-1
LOG_LEVEL=INFO
```

**Trigger:**
```bash
aws lambda create-event-source-mapping \
  --function-name canna-translator \
  --event-source-arn arn:aws:sqs:REGION:ACCOUNT_ID:canna-translation-queue.fifo \
  --batch-size 1
```

---

## Lambda Function Code

### Directory Structure

```
lambda-translator/
├── lambda_function.py  # Handler
├── translator.py       # OpenAI logic
├── db_manager.py       # PostgreSQL operations
├── config.py           # Configuration
└── requirements.txt
```

### Key Files

**config.py:**
```python
import os

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
SECRETS_MANAGER_DB_SECRET = 'canna/database/credentials'
SECRETS_MANAGER_OPENAI_SECRET = 'canna/openai/api-key'

OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 4000
OPENAI_TIMEOUT = 60

SUPPORTED_MODELS = ['Strain', 'Article', 'Terpene']
```

**translator.py - Key Method:**
```python
def get_system_prompt(self, model_name, source_lang, target_lang):
    """Generate bidirectional translation prompt"""
    return f"""You are a professional translator specializing in cannabis industry content.
Translate from {source_lang.upper()} to {target_lang.upper()}.

CRITICAL RULES:
1. Keep strain names UNCHANGED (e.g., "Northern Lights", "OG Kush")
2. Preserve ALL HTML tags exactly as they appear
3. Keep measurement units unchanged (%, mg/g, THC, CBD, CBG)
4. Maintain technical cannabis terminology accuracy
5. Preserve URLs and links
6. Keep special characters and symbols

OUTPUT FORMAT:
Return ONLY a valid JSON object with field names as keys and translations as values.
Example: {{"title": "translated title", "description": "translated description"}}

DO NOT include explanations, comments, or any text outside the JSON object.

{self._get_model_specific_instructions(model_name)}
"""

def _get_model_specific_instructions(self, model_name):
    instructions = {
        'Strain': 'STRAIN-SPECIFIC: Preserve genetic lineage terms (Indica, Sativa, Hybrid). Keep terpene names in English.',
        'Article': 'ARTICLE-SPECIFIC: Maintain journalistic tone. Keep H3 heading IDs unchanged.',
        'Terpene': 'TERPENE-SPECIFIC: Keep chemical compound names in English. Translate effects and descriptions.',
    }
    return instructions.get(model_name, '')
```

**lambda_function.py - Handler:**
```python
def lambda_handler(event, context):
    translator = Translator()
    db_manager = DatabaseManager()

    for record in event['Records']:
        message = json.loads(record['body'])
        model_name = message['model']
        instance_id = message['instance_id']
        fields = message['fields']
        direction = message.get('direction', 'en-to-es')  # Bidirectional support

        source_lang, target_lang = direction.split('-to-')
        source_hash = fields.pop('content_hash', None)

        # Translate via OpenAI
        translations = translator.translate(model_name, fields, source_lang, target_lang)

        # Update database
        db_manager.update_translation(
            model_name, instance_id, translations,
            source_hash, target_lang
        )

    return {'statusCode': 200}
```

**requirements.txt:**
```
openai==1.12.0
psycopg2-binary==2.9.9
boto3==1.35.17
botocore==1.35.17
```

**Deploy:**
```bash
cd lambda-translator
pip install -r requirements.txt -t package/
cp *.py package/
cd package && zip -r ../canna-translator.zip . && cd ..

aws lambda update-function-code \
  --function-name canna-translator \
  --zip-file fileb://canna-translator.zip
```

---

## Django Integration

### signals.py

**File:** `apps/strains/signals.py`

```python
import json
import boto3
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from apps.strains.models import Strain, Article, Terpene

def send_to_translation_queue(model_name, instance_id, fields, direction='en-to-es'):
    """Send translation job to SQS"""
    sqs = boto3.client('sqs', region_name=settings.AWS_REGION)

    message = {
        'model': model_name,
        'instance_id': instance_id,
        'fields': fields,
        'direction': direction,  # Bidirectional support
    }

    sqs.send_message(
        QueueUrl=settings.AWS_SQS_TRANSLATION_QUEUE_URL,
        MessageBody=json.dumps(message),
        MessageGroupId=f'{model_name}-translations',
        MessageDeduplicationId=f'{model_name}-{instance_id}-{fields.get("content_hash", "")}'
    )

@receiver(pre_save, sender=Strain)
def check_strain_translation_needed(sender, instance, **kwargs):
    """Mark as outdated if content changed"""
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
        if old.get_translatable_content_hash() != instance.get_translatable_content_hash():
            instance.translation_status = 'outdated'
    except sender.DoesNotExist:
        pass

@receiver(post_save, sender=Strain)
def queue_strain_translation(sender, instance, created, **kwargs):
    """Queue translation if needed"""
    if instance.needs_translation():
        fields = instance.get_translatable_fields()
        if fields:
            fields['content_hash'] = instance.get_translatable_content_hash()
            direction = getattr(settings, 'TRANSLATION_DIRECTION', 'en-to-es')
            send_to_translation_queue('Strain', instance.id, fields, direction)
            Strain.objects.filter(pk=instance.pk).update(translation_status='pending')

# Repeat for Article and Terpene
```

**Register in apps.py:**
```python
# apps/strains/apps.py
class StrainsConfig(AppConfig):
    name = 'apps.strains'

    def ready(self):
        import apps.strains.signals
```

---

### settings.py Updates

```python
# Add to settings.py

# AWS SQS Configuration
AWS_SQS_TRANSLATION_QUEUE_URL = os.getenv(
    'AWS_SQS_TRANSLATION_QUEUE_URL',
    'https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/canna-translation-queue.fifo'
)
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# Translation direction (change after Phase 2)
TRANSLATION_DIRECTION = os.getenv('TRANSLATION_DIRECTION', 'en-to-es')  # or 'es-to-en'

# Enable/disable signals
ENABLE_TRANSLATION_SIGNALS = os.getenv('ENABLE_TRANSLATION_SIGNALS', 'false').lower() == 'true'
```

---

## Management Commands

### 1. translate_existing_content

**Purpose:** Bulk translate existing content (Phase 2)

**Usage:**
```bash
python manage.py translate_existing_content --direction es-to-en
```

**Implementation:** See Phase 2 section above

---

### 2. check_translations

**Purpose:** Check translation status across all models

**File:** `apps/strains/management/commands/check_translations.py`

```python
from django.core.management.base import BaseCommand
from apps.strains.models import Strain, Article, Terpene

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true')
        parser.add_argument('--model', choices=['Strain', 'Article', 'Terpene', 'all'], default='all')

    def handle(self, *args, **options):
        for model in [Strain, Article, Terpene]:
            total = model.objects.count()
            pending = model.objects.filter(translation_status='pending').count()
            synced = model.objects.filter(translation_status='synced').count()
            failed = model.objects.filter(translation_status='failed').count()

            self.stdout.write(f'{model.__name__}: Total={total}, Synced={synced}, Pending={pending}, Failed={failed}')

            if options['fix']:
                for obj in model.objects.filter(translation_status='failed'):
                    obj.mark_translation_pending()
                self.stdout.write(self.style.SUCCESS(f'Requeued {failed} failed translations'))
```

**Usage:**
```bash
# Check status
python manage.py check_translations

# Check and requeue failed
python manage.py check_translations --fix
```

---

### 3. retry_failed_translations

**Purpose:** Retry failed translations

```bash
python manage.py retry_failed_translations --max 100
```

---

## Testing

### Test Translation Pipeline

**1. Create Test Strain:**
```python
python manage.py shell

from apps.strains.models import Strain
s = Strain.objects.create(
    name="Test Strain",
    title_en="Test Strain | Cannabis Information",
    description_en="This is a test strain for validating translation.",
    thc=20.0,
    category="Hybrid",
    active=True
)
print(f"Created #{s.id}, Status: {s.translation_status}")
```

**2. Check SQS:**
```bash
aws sqs get-queue-attributes \
  --queue-url https://sqs.REGION.amazonaws.com/ACCOUNT_ID/canna-translation-queue.fifo \
  --attribute-names ApproximateNumberOfMessages
```

**3. Monitor Lambda:**
```bash
aws logs tail /aws/lambda/canna-translator --follow
```

**4. Verify Translation:**
```python
s = Strain.objects.get(id=TEST_ID)
print(f"EN: {s.title_en}")
print(f"ES: {s.title_es}")
print(f"Status: {s.translation_status}")
```

---

## Monitoring

### CloudWatch Alarms

**Lambda Errors:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name canna-translation-lambda-errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=canna-translator
```

**DLQ Messages:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name canna-translation-dlq-messages \
  --metric-name ApproximateNumberOfMessagesVisible \
  --namespace AWS/SQS \
  --threshold 1 \
  --dimensions Name=QueueName,Value=canna-translation-dlq.fifo
```

**Queue Age:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name canna-translation-queue-age \
  --metric-name ApproximateAgeOfOldestMessage \
  --namespace AWS/SQS \
  --threshold 600 \
  --dimensions Name=QueueName,Value=canna-translation-queue.fifo
```

---

## Troubleshooting

### Common Issues

**Translations not appearing:**
```bash
# Check signals registered
python manage.py shell
>>> from django.db.models.signals import post_save
>>> from apps.strains.models import Strain
>>> post_save.has_listeners(Strain)  # Should be True

# Check SQS queue
aws sqs get-queue-attributes --queue-url <URL> --attribute-names All

# Check Lambda logs
aws logs tail /aws/lambda/canna-translator --since 1h
```

**Lambda timeout:**
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name canna-translator \
  --timeout 600
```

**Database connection failed:**
- Verify RDS security group allows Lambda
- Check Secrets Manager credentials
- Test connection from Lambda VPC

**Rate limit errors:**
- Increase pause in management command
- Check OpenAI tier and limits
- Monitor OpenAI dashboard

---

## Cost Estimation

### Monthly Costs

**OpenAI API (gpt-4o-mini):**
- Input: $0.150/1M tokens
- Output: $0.600/1M tokens
- Avg strain: ~650 input + 700 output tokens = $0.008
- 100 updates/month: **~$0.80/month**

**AWS Lambda:** Free tier (1M requests, 400k GB-seconds)

**AWS SQS:** Free tier (1M requests)

**AWS Secrets Manager:** $0.40/secret/month × 2 = **$0.80/month**

**CloudWatch Logs:** ~$0.50/month (5GB)

**Total: ~$2.10/month**

**One-time (initial translation):** ~1000 items × $0.008 = **~$8**

---

## Deployment Checklist

### Phase 1 (Complete ✅)
- [x] django-modeltranslation installed
- [x] Models with TranslationMixin
- [x] Migrations created and applied
- [x] Admin interface configured
- [x] Frontend language switcher
- [x] Django i18n configured

### Phase 2 (Pending ⏳)
- [ ] OpenAI API key obtained
- [ ] Management command created: `translate_existing_content`
- [ ] Bulk translation executed: ES→EN
- [ ] Translation quality verified
- [ ] Switch `TRANSLATION_DIRECTION` to `en-to-es`

### Phase 3 (Pending ⏳)
- [ ] AWS IAM roles created
- [ ] Secrets Manager configured
- [ ] SQS queues created (main + DLQ)
- [ ] Lambda function deployed
- [ ] Signals implemented and tested
- [ ] CloudWatch alarms configured
- [ ] End-to-end test passed
- [ ] Monitoring dashboard created
- [ ] Team trained on workflow

---

## Next Steps

1. **Phase 2:** Create `translate_existing_content` command
2. **Phase 2:** Execute bulk ES→EN translation on production
3. **Phase 3:** Set up AWS infrastructure (SQS, Lambda, IAM)
4. **Phase 3:** Deploy Lambda function
5. **Phase 3:** Implement and test signals
6. **Phase 3:** Monitor and optimize

---

**Version:** 1.0
**Last Updated:** 2025-10-09
**For admin usage:** See `ADMIN_GUIDE.md`
