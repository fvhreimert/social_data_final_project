# File: tmdb_worker.py
import time
from tmdbv3api import TMDb, Movie, Find
import requests # For more specific exception handling if needed

def fetch_release_date_tmdb_balanced(title_id, api_key):
    # Initialize TMDb objects within the worker.
    # This is generally safer for multiprocessing.
    tmdb_worker = TMDb()
    tmdb_worker.api_key = api_key
    tmdb_worker.language = 'en'
    # tmdb_worker.debug = False

    find_worker = Find()
    movie_api_worker = Movie()

    if not title_id or not isinstance(title_id, str) or not title_id.startswith('tt'):
        return title_id, None, "INVALID_ID" # Add a status

    # --- Configurable Retry Logic ---
    # For 429 (Rate Limit) errors
    max_retries_rate_limit = 5  # Max attempts for rate limit errors
    initial_delay_rate_limit = 10 # Initial delay in seconds for 429
    backoff_factor_rate_limit = 1.5 # Multiplier for delay (e.g., 10s, 15s, 22.5s...)

    # For other transient errors (e.g., network timeout, 5xx server errors)
    max_retries_other = 2       # Fewer retries for other potentially transient errors
    delay_other_error = 5       # Fixed delay for these

    current_delay_rate_limit = initial_delay_rate_limit

    for attempt in range(max_retries_rate_limit + 1): # Total attempts for rate limit
        try:
            results = find_worker.find(external_id=title_id, external_source='imdb_id')

            if results.get('movie_results'):
                tmdb_id_val = results['movie_results'][0]['id']
                movie_details = movie_api_worker.details(tmdb_id_val)
                release_date_str = movie_details.get('release_date')
                if release_date_str and len(release_date_str) > 0:
                    # SUCCESS: No sleep here, let the main loop control overall rate if needed
                    # or rely on NUM_WORKERS * natural_api_call_time to stay within limits.
                    return title_id, release_date_str, "SUCCESS"
                else:
                    # Found movie, but no release date string
                    return title_id, None, "NO_DATE_FIELD"
            else:
                # Movie not found by /find endpoint (treat as 404 equivalent)
                # No retry needed for this.
                return title_id, None, "NOT_FOUND_FIND"

        except requests.exceptions.HTTPError as e_http: # More specific error from tmdbv3api likely wraps this
            status_code = e_http.response.status_code if e_http.response is not None else None
            error_context = f"HTTPError (Status: {status_code})"

            if status_code == 401: # Unauthorized - API key issue
                print(f"Worker for {title_id}: Unauthorized (401). Check API Key. Stopping retries for this ID.")
                return title_id, None, "ERROR_401_UNAUTHORIZED"
            elif status_code == 404: # Not Found
                # print(f"Worker for {title_id}: Not Found (404) from API. No retry.")
                return title_id, None, "ERROR_404_NOT_FOUND"
            elif status_code == 429: # Rate Limit Exceeded
                if attempt < max_retries_rate_limit:
                    print(f"Worker for {title_id}: Rate limit (429). Attempt {attempt + 1}/{max_retries_rate_limit + 1}. Sleeping for {current_delay_rate_limit:.1f}s...")
                    time.sleep(current_delay_rate_limit)
                    current_delay_rate_limit *= backoff_factor_rate_limit
                    continue # Go to next iteration of the retry loop
                else:
                    print(f"Worker for {title_id}: Max retries for rate limit (429) reached.")
                    return title_id, None, "ERROR_429_MAX_RETRIES"
            else: # Other HTTP errors (500, 503, etc.)
                if attempt < max_retries_other: # Use different retry count for these
                    print(f"Worker for {title_id}: {error_context}. Attempt {attempt + 1}/{max_retries_other + 1}. Sleeping for {delay_other_error}s...")
                    time.sleep(delay_other_error)
                    continue
                else:
                    print(f"Worker for {title_id}: Max retries for {error_context} reached.")
                    return title_id, None, f"ERROR_HTTP_{status_code}_MAX_RETRIES"

        except Exception as e: # Catch-all for other exceptions (network issues, JSON parsing, etc.)
            # This could be a temporary network hiccup or an unexpected API response.
            if attempt < max_retries_other:
                print(f"Worker for {title_id}: Generic error '{type(e).__name__}: {e}'. Attempt {attempt + 1}/{max_retries_other + 1}. Sleeping for {delay_other_error}s...")
                time.sleep(delay_other_error)
                continue # Retry for generic errors
            else:
                print(f"Worker for {title_id}: Max retries for generic error '{type(e).__name__}' reached.")
                return title_id, None, "ERROR_GENERIC_MAX_RETRIES"
                
    # Should only be reached if all retries for 429 are exhausted without specific return
    return title_id, None, "ERROR_MAX_RETRIES_UNHANDLED_EXIT"