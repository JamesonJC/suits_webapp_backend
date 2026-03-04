import threading

# Thread-local storage ensures tenant info is per-request and not shared between threads
_thread_locals = threading.local()

def set_current_tenant(tenant):
    """
    Sets the current tenant for this thread/request.
    Called by middleware when a request arrives with a tenant code.
    """
    _thread_locals.current_tenant = tenant

def get_current_tenant():
    """
    Returns the current tenant for this thread/request.
    Returns None if no tenant has been set.
    Used in Tenant-aware QuerySets and Managers to automatically filter queries.
    """
    return getattr(_thread_locals, "current_tenant", None)

def clear_current_tenant():
    """
    Clears the tenant from the current thread.
    Useful for tests or manual cleanup after a request finishes.
    """
    if hasattr(_thread_locals, "current_tenant"):
        del _thread_locals.current_tenant