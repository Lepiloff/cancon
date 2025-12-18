# GeoIP2 Database Setup

This directory contains the MaxMind GeoLite2 database for IP-based language detection.

## Required File

Download `GeoLite2-Country.mmdb` and place it in this directory.

## How to Download

1. **Create MaxMind Account**: Register at https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
2. **Generate License Key**: Create a license key in your account
3. **Download Database**:
   ```bash
   # Option 1: Direct download (requires account)
   # Download from: https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key=YOUR_LICENSE_KEY&suffix=tar.gz

   # Option 2: Using curl (replace YOUR_LICENSE_KEY)
   curl -o GeoLite2-Country.tar.gz "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key=YOUR_LICENSE_KEY&suffix=tar.gz"

   # Extract the .mmdb file
   tar -xzf GeoLite2-Country.tar.gz
   cp GeoLite2-Country_*/GeoLite2-Country.mmdb ./
   ```

## File Structure
```
geoip/
├── README.md (this file)
└── GeoLite2-Country.mmdb (download required)
```

## Docker Production
For production deployment, ensure the database file is available:

### Option 1: Include in image
Place the file in this directory before building Docker image.

### Option 2: Download during build
Add to Dockerfile:
```dockerfile
# Download GeoLite2 during build (requires build arg for license key)
ARG MAXMIND_LICENSE_KEY
RUN curl -o /tmp/GeoLite2-Country.tar.gz "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz" && \
    tar -xzf /tmp/GeoLite2-Country.tar.gz -C /tmp && \
    cp /tmp/GeoLite2-Country_*/GeoLite2-Country.mmdb /app/geoip/ && \
    rm -rf /tmp/GeoLite2-Country*
```

### Option 3: Volume mount
Mount the database file as a volume in production.

## Notes
- Database updates monthly (free version)
- File size: ~6MB
- IP geolocation accuracy: Country level (~99.8%)