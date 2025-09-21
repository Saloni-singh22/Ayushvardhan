# 🏥 NAMASTE & ICD-11 TM2 Integration API

## 📋 Project Overview

A **FHIR R4-compliant terminology microservice** that seamlessly integrates India's NAMASTE (National AYUSH Morbidity & Standardized Terminologies Electronic) codes with WHO's ICD-11 Traditional Medicine Module 2 (TM2) and Biomedicine modules. This solution enables **dual-coding support** for traditional medicine (Ayurveda, Siddha, Unani) and biomedical systems while ensuring full compliance with **India's 2016 EHR Standards**.

### 🎯 Mission Statement
*Bridging traditional and modern medicine through standardized, interoperable digital health terminologies that empower clinicians, enable insurance claims, and provide real-time analytics for evidence-based healthcare policy.*

---

## 🌟 Key Features

### 🔄 **Dual-Coding Support**
- **NAMASTE Codes**: 4,500+ standardized terms for Ayurveda, Siddha, and Unani
- **WHO ICD-11 TM2**: 529 disorder categories + 196 pattern codes
- **ICD-11 Biomedicine**: Complete biomedical classification
- **Intelligent Mapping**: AI-powered translation between coding systems

### 🔐 **Security & Compliance**
- **ABHA OAuth 2.0**: Secure authentication with 14-digit ABHA integration
- **Public Key Encryption**: End-to-end security for sensitive data
- **India EHR Standards 2016**: Full compliance with national requirements
- **ISO 22600**: Access control and audit trails
- **GDPR-ready**: Consent management and data protection

### 🚀 **FHIR R4 Compliance**
- **CodeSystem Resources**: NAMASTE and WHO terminologies
- **ConceptMap Resources**: Bidirectional mapping support
- **ValueSet Resources**: Auto-complete and search functionality
- **Bundle Resources**: Encounter uploads with dual coding
- **Terminology Operations**: $lookup, $validate-code, $translate, $expand, $subsumes

### 🌐 **Real-time Integration**
- **WHO ICD-11 2025 API**: Live synchronization with latest updates
- **NAMASTE Portal**: Direct CSV import and processing
- **Version Tracking**: Automatic updates and change management
- **Multi-lingual Support**: Hindi, English, and regional languages

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Clinical EMR  │    │  FHIR Terminology│    │  External APIs  │
│   Systems       │◄──►│  Microservice    │◄──►│  (WHO/ABHA)    │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Auto-complete │    │   Dual Coding   │    │   Real-time     │
│   Search        │    │   Translation   │    │   Sync          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🔧 **Technical Stack**
- **Backend**: FastAPI 0.115.0 (Python 3.11+)
- **Database**: MongoDB 7.0+ with Motor async driver
- **Validation**: Pydantic 2.9.0 with FHIR R4 schemas
- **Authentication**: OAuth 2.0 with ABHA integration
- **Containerization**: Docker & Kubernetes
- **Monitoring**: Prometheus + Grafana

---

## 📚 Problem Statement

### 🔍 **Background**
India's Ayush sector is transitioning from paper-based records to interoperable digital health systems. This transformation requires harmonizing two critical coding systems:

1. **NAMASTE Codes**: 4,500+ standardized terms for traditional medicine
2. **WHO ICD-11 TM2**: Global framework for traditional medicine disorders
3. **ICD-11 Biomedicine**: International biomedical classification

### 🎯 **Challenges Addressed**
- **Interoperability Gap**: No standardized bridge between traditional and biomedical coding
- **Compliance Requirements**: India's 2016 EHR Standards mandate FHIR R4 APIs
- **Insurance Integration**: Global ICD-11 coding required for claims processing
- **Clinical Decision Support**: Need for dual-coding in EMR systems
- **Analytics & Reporting**: Real-time morbidity data for policy decisions

### 💡 **Solution Benefits**
- **Enhanced Patient Care**: Comprehensive traditional + biomedical records
- **Insurance Compatibility**: Global ICD-11 compliance for claims
- **Research Enablement**: Standardized data for evidence-based studies
- **Policy Support**: Real-time analytics for Ministry of Ayush
- **Global Interoperability**: WHO-compliant terminology integration

---

## 🚀 Core Functionality

### 1. **FHIR Terminology Service**
```http
GET /fhir/CodeSystem              # Retrieve NAMASTE/WHO terminologies
GET /fhir/ConceptMap              # Access mapping relationships
POST /fhir/ConceptMap/$translate  # Translate NAMASTE ↔ TM2 codes
GET /fhir/ValueSet/$expand        # Auto-complete functionality
POST /fhir/Bundle                 # Upload encounters with dual coding
```

### 2. **Auto-complete Search**
```json
{
  "query": "fever",
  "results": [
    {
      "namaste_code": "NAM_001_234",
      "display": "Jwara (Fever)",
      "system": "Ayurveda",
      "icd11_tm2": "TM2.F01.2",
      "icd11_bio": "R50.9",
      "confidence": 0.95
    }
  ]
}
```

### 3. **Dual Coding Translation**
```json
{
  "source_code": "NAM_001_234",
  "source_system": "NAMASTE",
  "target_system": "ICD-11-TM2",
  "target_code": "TM2.F01.2",
  "mapping_confidence": 0.93,
  "biomedical_equivalent": "R50.9"
}
```

### 4. **ABHA Integration**
```json
{
  "abha_number": "12345678901234",
  "authentication": "OAuth 2.0",
  "encryption": "Public Key",
  "consent_status": "granted",
  "audit_trail": "enabled"
}
```

---

## 📊 Technical Specifications

### 🔧 **API Endpoints**

| Endpoint | Method | Purpose | FHIR Operation |
|----------|--------|---------|----------------|
| `/fhir/CodeSystem` | GET | Retrieve terminologies | Read |
| `/fhir/CodeSystem/$lookup` | POST | Code details lookup | $lookup |
| `/fhir/CodeSystem/$validate-code` | POST | Validate codes | $validate-code |
| `/fhir/ConceptMap` | GET | Mapping resources | Read |
| `/fhir/ConceptMap/$translate` | POST | Code translation | $translate |
| `/fhir/ValueSet/$expand` | POST | Auto-complete | $expand |
| `/fhir/Bundle` | POST | Encounter upload | Create |
| `/api/v1/search` | GET | Auto-complete search | Custom |
| `/api/v1/sync` | POST | Data synchronization | Custom |

### 🏗️ **Database Schema**

#### FHIR CodeSystem Collection
```json
{
  "_id": "namaste-ayurveda-v1",
  "resourceType": "CodeSystem",
  "url": "https://namaste.gov.in/fhir/CodeSystem/ayurveda",
  "version": "1.0.0",
  "name": "NAMASTE_Ayurveda",
  "title": "NAMASTE Ayurveda Terminology",
  "status": "active",
  "concept": [
    {
      "code": "NAM_001_234",
      "display": "Jwara (Fever)",
      "definition": "Fever in Ayurvedic context"
    }
  ]
}
```

#### ConceptMap Collection
```json
{
  "_id": "namaste-to-icd11-tm2",
  "resourceType": "ConceptMap",
  "url": "https://namaste.gov.in/fhir/ConceptMap/namaste-icd11-tm2",
  "sourceUri": "https://namaste.gov.in/fhir/CodeSystem/ayurveda",
  "targetUri": "http://id.who.int/icd/release/11/mms/tm2",
  "group": [
    {
      "source": "https://namaste.gov.in/fhir/CodeSystem/ayurveda",
      "target": "http://id.who.int/icd/release/11/mms/tm2",
      "element": [
        {
          "code": "NAM_001_234",
          "target": [
            {
              "code": "TM2.F01.2",
              "equivalence": "equivalent",
              "confidence": 0.95
            }
          ]
        }
      ]
    }
  ]
}
```

### 🔐 **Security Implementation**

#### ABHA OAuth 2.0 Flow
```python
class ABHAAuthService:
    async def authenticate(self, abha_number: str) -> AuthToken:
        # 1. Validate 14-digit ABHA number
        # 2. Fetch public key from ABHA API
        # 3. Encrypt sensitive data
        # 4. Generate OAuth 2.0 token
        # 5. Return secure session
```

#### Audit Trail Schema
```json
{
  "timestamp": "2025-09-21T10:30:00Z",
  "user_id": "ABHA_12345678901234",
  "action": "code_translation",
  "resource": "/fhir/ConceptMap/$translate",
  "input": "NAM_001_234",
  "output": "TM2.F01.2",
  "consent_id": "CONSENT_789",
  "ip_address": "192.168.1.100"
}
```

---

## 🚀 Getting Started

### 📋 **Prerequisites**
- Python 3.11+
- MongoDB 7.0+
- Docker & Docker Compose
- WHO ICD-11 API credentials
- ABHA API access tokens

### ⚡ **Quick Start**

1. **Clone Repository**
```bash
git clone https://github.com/Saloni-singh22/Ayushvardhan.git
cd Ayushvardhan
```

2. **Environment Setup**
```bash
cp .env.example .env
# Configure API credentials in .env file
```

3. **Docker Deployment**
```bash
docker-compose up -d
```

4. **Access API**
```bash
curl http://localhost:8000/fhir/metadata
```

### 🔧 **Development Setup**

1. **Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Database Setup**
```bash
python scripts/init_database.py
```

4. **Run Development Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📈 Usage Examples

### 🔍 **Auto-complete Search**
```python
import httpx

async def search_terminology(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/search",
            params={"q": query, "limit": 10}
        )
        return response.json()

# Search for fever-related terms
results = await search_terminology("fever")
```

### 🔄 **Code Translation**
```python
async def translate_code(source_code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/fhir/ConceptMap/$translate",
            json={
                "resourceType": "Parameters",
                "parameter": [
                    {"name": "system", "valueUri": "https://namaste.gov.in/fhir/CodeSystem/ayurveda"},
                    {"name": "code", "valueCode": source_code},
                    {"name": "target", "valueUri": "http://id.who.int/icd/release/11/mms/tm2"}
                ]
            }
        )
        return response.json()

# Translate NAMASTE code to ICD-11 TM2
translation = await translate_code("NAM_001_234")
```

### 📦 **Bundle Upload**
```python
def create_dual_coded_encounter():
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "code": {
                        "coding": [
                            {
                                "system": "https://namaste.gov.in/fhir/CodeSystem/ayurveda",
                                "code": "NAM_001_234",
                                "display": "Jwara (Fever)"
                            },
                            {
                                "system": "http://id.who.int/icd/release/11/mms/tm2",
                                "code": "TM2.F01.2",
                                "display": "Fever patterns"
                            },
                            {
                                "system": "http://id.who.int/icd/release/11/mms",
                                "code": "R50.9",
                                "display": "Fever, unspecified"
                            }
                        ]
                    }
                }
            }
        ]
    }
```

---

## 🧪 Testing

### 🔬 **Test Coverage**
- **Unit Tests**: 95%+ coverage
- **Integration Tests**: API endpoint validation
- **FHIR Compliance**: Official FHIR test suite
- **Performance Tests**: Load testing up to 1000 RPS

### 🚀 **Running Tests**
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# FHIR compliance tests
pytest tests/fhir_compliance/

# Performance tests
pytest tests/performance/
```

### 📊 **Test Reports**
```bash
# Coverage report
pytest --cov=app --cov-report=html

# FHIR validation report
python scripts/validate_fhir_compliance.py
```

---

## 🚀 Deployment

### 🐳 **Docker Deployment**
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongodb:27017
      - WHO_API_KEY=${WHO_API_KEY}
      - ABHA_CLIENT_ID=${ABHA_CLIENT_ID}
    depends_on:
      - mongodb
      
  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
```

### ☸️ **Kubernetes Deployment**
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: namaste-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: namaste-api
  template:
    metadata:
      labels:
        app: namaste-api
    spec:
      containers:
      - name: api
        image: namaste-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URL
          value: "mongodb://mongodb-service:27017"
```

### 📊 **Monitoring**
- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus integration
- **Logging**: Structured JSON logs
- **Alerts**: Critical error notifications

---

## 📊 Performance Metrics

### 🎯 **Target Performance**
- **Response Time**: < 200ms (95th percentile)
- **Throughput**: 1000+ requests/second
- **Availability**: 99.9% uptime
- **Data Accuracy**: 95%+ mapping confidence

### 📈 **Scalability**
- **Horizontal Scaling**: Kubernetes auto-scaling
- **Database Sharding**: MongoDB cluster support
- **Caching**: Redis for frequently accessed data
- **CDN**: Global content delivery

---

## 🤝 Contributing

### 🛠️ **Development Workflow**
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Run full test suite
5. Submit pull request

### 📝 **Code Standards**
- **Python**: Black formatting, flake8 linting
- **Type Hints**: mypy validation
- **Documentation**: Comprehensive docstrings
- **Testing**: Minimum 90% coverage

### 🔍 **Code Review Process**
- Automated CI/CD checks
- FHIR compliance validation
- Security vulnerability scanning
- Performance impact assessment

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Support & Contact

### 🆘 **Getting Help**
- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/Saloni-singh22/Ayushvardhan/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Saloni-singh22/Ayushvardhan/discussions)

### 📧 **Contact**
- **Project Lead**: [Saloni Singh](https://github.com/Saloni-singh22)
- **Email**: [Contact Email]
- **Website**: [Project Website]

### 🏢 **Acknowledgments**
- **Ministry of Ayush**: NAMASTE terminology support
- **WHO**: ICD-11 TM2 module guidance
- **ABDM**: ABHA integration support
- **HL7 FHIR Community**: Standards compliance

---

## 🗺️ Roadmap

### 📅 **Phase 1: Foundation (Q3 2025)**
- ✅ Core FHIR R4 implementation
- ✅ NAMASTE data integration
- ✅ WHO ICD-11 API connection
- ✅ ABHA authentication

### 📅 **Phase 2: Enhancement (Q4 2025)**
- 🔄 AI-powered mapping improvements
- 🔄 Multi-lingual interface
- 🔄 Advanced analytics dashboard
- 🔄 Mobile app integration

### 📅 **Phase 3: Scale (Q1 2026)**
- 📋 Multi-tenant architecture
- 📋 Regional deployment
- 📋 Performance optimization
- 📋 Enterprise features

---

## 📈 Impact & Vision

### 🌟 **Expected Impact**
- **Healthcare Providers**: Seamless traditional-modern integration
- **Patients**: Comprehensive health records
- **Researchers**: Standardized data for studies
- **Policymakers**: Evidence-based decision making
- **Global Community**: WHO-compliant traditional medicine data

### 🔮 **Future Vision**
Creating a global standard for traditional medicine informatics that bridges ancient wisdom with modern healthcare technology, enabling evidence-based traditional medicine practice and research worldwide.

---

*Built with ❤️ for advancing traditional medicine through modern technology*