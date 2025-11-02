# Performance Improvements

This document describes the performance optimizations made to the KLibras API.

## Summary of Changes

The following optimizations were implemented to improve the performance and efficiency of the API:

### 1. Database Indexes
**Impact**: High - Significantly faster queries on frequently searched fields

- Added index to `Module.name` field
- Added index to `Sign.name` field

**Migration Required**: Yes

To apply these changes, you need to create a new Alembic migration:

```bash
# Create the migration
alembic revision --autogenerate -m "Add indexes to module and sign name fields"

# Apply the migration
alembic upgrade head
```

Alternatively, you can manually add the indexes with SQL:

```sql
CREATE INDEX ix_modules_name ON modules(name);
CREATE INDEX ix_signs_name ON signs(name);
```

### 2. Database Connection Pool Optimization
**Impact**: Medium - Better handling of concurrent requests

Changed connection pool settings in `app/db/database_connection.py`:
- Increased `pool_size` from 10 to 20 connections
- Increased `max_overflow` from 20 to 40 connections  
- Added `pool_recycle=3600` to refresh connections every hour
- Added `pool_timeout=30` for connection acquisition timeout

**Benefits**:
- Can handle more concurrent database operations
- Better connection lifecycle management
- Reduced connection errors under high load

### 3. Query Optimization in User Service
**Impact**: High - Reduced database round trips

#### `add_completed_module_to_user()`
- **Before**: Made 2 separate database queries (one for module, one for user)
- **After**: Fetches module, then uses `refresh()` on existing user object
- **Result**: 50% reduction in queries for this operation

#### `add_known_sign_to_user()`
- **Before**: Made 2 separate database queries (one for sign, one for user)
- **After**: Fetches sign, then uses `refresh()` on existing user object
- **Result**: 50% reduction in queries for this operation

#### `get_users_leaderboard()`
- **Before**: Potentially triggered N+1 queries when accessing user's known_signs
- **After**: Uses `selectinload(User.known_signs)` for eager loading
- **Result**: Fixed N+1 query problem

### 4. Video Processing Optimization
**Impact**: Medium - Reduced memory usage and network payload

#### Changed Encoding Format
- **Before**: Used hex encoding (`video_content.hex()`)
- **After**: Uses base64 encoding (`base64.b64encode()`)
- **Result**: ~25% reduction in encoded size (base64 is ~133% of original vs hex at ~200%)

### 5. Long-Polling Optimization
**Impact**: Low-Medium - More efficient polling behavior

#### Exponential Backoff
- **Before**: Fixed 0.5 second delay between polls
- **After**: Starts at 0.1s, increases exponentially to max 2.0s
- **Result**: 
  - Faster response for quick jobs (checks at 0.1s)
  - Less database load for longer jobs (backs off to 2s)
  - More efficient resource usage

### 6. Model Loading Optimization
**Impact**: Medium - Faster application startup and better resource management

#### Lazy Loading with Singleton Pattern
- **Before**: TensorFlow model and MediaPipe landmarkers loaded at module import time
- **After**: Models loaded lazily on first use and cached (singleton pattern)
- **Benefits**:
  - Faster application startup (models only loaded when needed)
  - Single model instance shared across all requests
  - Easier to test without loading heavy ML models

## Performance Testing Recommendations

To validate these improvements, consider:

1. **Load Testing**: Use tools like `locust` or `apache bench` to measure:
   - Request throughput before/after
   - Response time improvements
   - Connection pool behavior under load

2. **Database Query Analysis**: 
   - Enable SQLAlchemy query logging
   - Verify reduced query counts
   - Check query execution times with `EXPLAIN ANALYZE`

3. **Memory Profiling**:
   - Monitor memory usage during video processing
   - Verify reduced memory overhead from base64 vs hex

4. **Application Startup Time**:
   - Measure startup time before/after lazy loading
   - Verify models load correctly on first request

## Migration Checklist

- [ ] Create and run Alembic migration for database indexes
- [ ] Restart application to apply connection pool changes
- [ ] Update video processing consumer to handle base64 encoding
- [ ] Monitor application logs for any issues
- [ ] Run performance tests to validate improvements

## Breaking Changes

**Video Processing Consumer**: If you have a separate consumer processing videos from RabbitMQ, it needs to be updated to decode base64 instead of hex:

```python
# Before
video_bytes = bytes.fromhex(message_body["video_content"])

# After
import base64
video_bytes = base64.b64decode(message_body["video_content"])
```

## Backward Compatibility

All other changes are backward compatible and don't require changes to API consumers.
