# File: tmdb_data.py
import pandas as pd
import time
import os
import multiprocessing
from functools import partial
from tmdb_worker import fetch_release_date_tmdb_balanced # Ensure tmdb_worker.py is in the same directory

# --- Configuration ---
# API Key - Using the provided key directly as requested.
# For production/shared code, environment variables are strongly recommended.
TMDB_API_KEY = "d64993a9f8d47eb7f6e6e426f7d1f63d"
if not TMDB_API_KEY or TMDB_API_KEY == 'YOUR_FALLBACK_TMDB_API_KEY_HERE': # Check if it's still a placeholder
    print("CRITICAL WARNING: API Key is a placeholder or missing. Please ensure a valid key is used.")
    # exit("TMDB API Key not configured. Exiting.")


# File Paths (Robustly defined)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..")) 

INPUT_FILE = os.path.join(PROJECT_ROOT, "data", "movies.parquet") # Original source
OUTPUT_FILE_WITH_DATES = os.path.join(PROJECT_ROOT, "data", "movies_with_release_dates_status_filtered.parquet") # Intermediate and final output
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "data", "movies_processed_ids_status_filtered.txt")

# Processing Parameters
NUM_WORKERS = 10  # Adjust based on API response (429 errors)

# --- Filtering Parameters ---
MIN_RELEASE_YEAR = 1980         # Exclude movies released before this year
MIN_VOTE_COUNT = 100            # Exclude movies with fewer than this many votes
RELEVANT_MOVIE_GENRES = [
    'Drama', 'Comedy', 'Documentary', 'Romance', 'Action',
    'Crime', 'Thriller', 'Horror', 'Adventure', 'Mystery', 'Sci-Fi', 'Fantasy'
]

# --- Main Processing Logic ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

    # --- Load DataFrame (Prioritize last saved output, then original input) ---
    df_original = None # Initialize
    if os.path.exists(OUTPUT_FILE_WITH_DATES):
        try:
            print(f"Attempting to load previously saved data from: {OUTPUT_FILE_WITH_DATES}")
            df_original = pd.read_parquet(OUTPUT_FILE_WITH_DATES)
            print(f"Successfully loaded {len(df_original)} records from {OUTPUT_FILE_WITH_DATES}.")
            if 'title_id' not in df_original.columns: 
                print(f"CRITICAL ERROR: 'title_id' column missing in loaded {OUTPUT_FILE_WITH_DATES}. Cannot proceed.")
                exit()
        except Exception as e:
            print(f"WARNING: Failed to load from {OUTPUT_FILE_WITH_DATES} (error: {e}). Will try loading original input file.")
            df_original = None 

    if df_original is None: 
        if not os.path.exists(INPUT_FILE):
            print(f"CRITICAL ERROR: Input file not found at {INPUT_FILE} and no previous output file to resume from.")
            exit()
        try:
            print(f"Loading original data from: {INPUT_FILE}")
            df_original = pd.read_parquet(INPUT_FILE)
            print(f"Successfully loaded {len(df_original)} movies from {INPUT_FILE}")
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to read original Parquet file {INPUT_FILE}. Error: {e}")
            exit()

    # --- Initialize Columns in the DataFrame (df_original) ---
    if 'release_date_full' not in df_original.columns:
        df_original['release_date_full'] = pd.NA
        print("Added 'release_date_full' column to df_original.")
    if 'fetch_status' not in df_original.columns:
        df_original['fetch_status'] = pd.NA
        print("Added 'fetch_status' column to df_original.")
    # --- End of DataFrame Loading and Initialization ---

    # --- Apply Filters ---
    print("\n--- Applying Filters ---")
    df_processing_candidates = df_original.copy() 

    if 'release_year' in df_processing_candidates.columns and MIN_RELEASE_YEAR is not None:
        df_processing_candidates['release_year'] = pd.to_numeric(df_processing_candidates['release_year'], errors='coerce')
        original_count_before_year_filter = len(df_processing_candidates)
        df_processing_candidates.dropna(subset=['release_year'], inplace=True)
        df_processing_candidates = df_processing_candidates[df_processing_candidates['release_year'] >= MIN_RELEASE_YEAR]
        print(f"Filtered by release_year >= {MIN_RELEASE_YEAR}: {original_count_before_year_filter} -> {len(df_processing_candidates)} movies")
    elif MIN_RELEASE_YEAR is not None:
        print(f"WARNING: 'release_year' column not found. Skipping year filter (MIN_RELEASE_YEAR = {MIN_RELEASE_YEAR}).")

    if 'vote_count' in df_processing_candidates.columns and MIN_VOTE_COUNT is not None:
        df_processing_candidates['vote_count'] = pd.to_numeric(df_processing_candidates['vote_count'], errors='coerce')
        original_count_before_vote_filter = len(df_processing_candidates)
        df_processing_candidates.dropna(subset=['vote_count'], inplace=True)
        df_processing_candidates = df_processing_candidates[df_processing_candidates['vote_count'] >= MIN_VOTE_COUNT]
        print(f"Filtered by vote_count >= {MIN_VOTE_COUNT}: {original_count_before_vote_filter} -> {len(df_processing_candidates)} movies")
    elif MIN_VOTE_COUNT is not None:
        print(f"WARNING: 'vote_count' column not found. Skipping vote count filter (MIN_VOTE_COUNT = {MIN_VOTE_COUNT}).")

    if 'genre' in df_processing_candidates.columns and RELEVANT_MOVIE_GENRES:
        original_count_before_genre_filter = len(df_processing_candidates)
        df_processing_candidates.dropna(subset=['genre'], inplace=True)
        df_processing_candidates['genre'] = df_processing_candidates['genre'].astype(str)
        relevant_genres_set = set(RELEVANT_MOVIE_GENRES)
        genre_mask = df_processing_candidates['genre'].apply(
            lambda x: any(g.strip() in relevant_genres_set for g in x.split(','))
        )
        df_processing_candidates = df_processing_candidates[genre_mask]
        print(f"Filtered by relevant genres: {original_count_before_genre_filter} -> {len(df_processing_candidates)} movies")
    elif RELEVANT_MOVIE_GENRES:
        print("WARNING: 'genre' column not found. Skipping genre filter.")
    
    print(f"Movies in df_original (source for status): {len(df_original)}, Movies to consider for API processing after content filters: {len(df_processing_candidates)}")
    # --- End of Filtering ---

    # --- Determine IDs to Process ---
    processed_ids_from_file = set()
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            processed_ids_from_file = set(line.strip() for line in f)
    print(f"Loaded {len(processed_ids_from_file)} IDs from progress file (attempted at least once).")

    candidate_title_ids_after_filters = df_processing_candidates['title_id'].unique()
    
    ids_to_process_list = []
    retryable_statuses = [ 
        "ERROR_429_MAX_RETRIES", "ERROR_HTTP_500_MAX_RETRIES", 
        "ERROR_HTTP_503_MAX_RETRIES", "ERROR_GENERIC_MAX_RETRIES",
        "ERROR_MAX_RETRIES_UNHANDLED_EXIT" 
    ]
    
    df_original_indexed = df_original.set_index('title_id')

    for tid in candidate_title_ids_after_filters:
        if tid not in processed_ids_from_file:
            ids_to_process_list.append(tid)
            continue

        current_status = pd.NA 
        if tid in df_original_indexed.index:
            # Ensure 'fetch_status' exists before trying to access it
            if 'fetch_status' in df_original_indexed.columns:
                 current_status = df_original_indexed.loc[tid, 'fetch_status']
            else: # fetch_status column might not exist if loading from a very old output or fresh input
                ids_to_process_list.append(tid) # Process if status column is missing for this ID
                continue
        else: # ID from filtered candidates not in main df_original_indexed (should be rare)
            ids_to_process_list.append(tid) # Process to be safe
            continue
        
        if pd.isna(current_status) or current_status in retryable_statuses:
            ids_to_process_list.append(tid)

    title_ids_to_process = list(set(ids_to_process_list))
    print(f"Number of title_ids to actually process via API (after filters & status check): {len(title_ids_to_process)}")

    if not title_ids_to_process:
        print("No new or retryable title_ids to process based on current filters and status. Exiting.")
    else:
        start_time_session = time.time()
        worker_func_with_api_key = partial(fetch_release_date_tmdb_balanced, api_key=TMDB_API_KEY)
        chunk_size = NUM_WORKERS * 20 
        processed_count_session = 0
        total_to_process_session = len(title_ids_to_process)
        session_processed_ids_log = set() 

        with multiprocessing.Pool(processes=NUM_WORKERS) as pool:
            try:
                for i in range(0, total_to_process_session, chunk_size):
                    current_chunk_ids_batch = title_ids_to_process[i:i + chunk_size]
                    if not current_chunk_ids_batch:
                        continue

                    print(f"\nProcessing chunk of {len(current_chunk_ids_batch)} items (starting with {current_chunk_ids_batch[0]})...")
                    
                    for title_id, date_str, status_str in pool.imap_unordered(worker_func_with_api_key, current_chunk_ids_batch):
                        processed_count_session += 1
                        
                        # Find index in df_original to update. Using .loc for safety with non-unique potential or if index reset.
                        idx_to_update = df_original[df_original['title_id'] == title_id].index
                        if not idx_to_update.empty:
                            df_original.loc[idx_to_update, 'release_date_full'] = date_str if date_str else pd.NA
                            df_original.loc[idx_to_update, 'fetch_status'] = status_str
                        else:
                            print(f"Warning: title_id {title_id} not found in df_original for update. This should not happen.")

                        if title_id not in processed_ids_from_file and title_id not in session_processed_ids_log:
                             with open(PROGRESS_FILE, 'a') as pf:
                                pf.write(f"{title_id}\n")
                             session_processed_ids_log.add(title_id)

                        if processed_count_session % (NUM_WORKERS * 2) == 0 or processed_count_session == total_to_process_session:
                            elapsed_time_session = time.time() - start_time_session
                            avg_time_per_item = elapsed_time_session / processed_count_session if processed_count_session > 0 else 0
                            items_remaining = total_to_process_session - processed_count_session
                            eta_seconds = items_remaining * avg_time_per_item if avg_time_per_item > 0 else "N/A"
                            eta_str = time.strftime("%H:%M:%S", time.gmtime(eta_seconds)) if isinstance(eta_seconds, (int, float)) and eta_seconds > 0 else "N/A"
                            
                            print(f"Processed {processed_count_session}/{total_to_process_session} "
                                  f"({processed_count_session*100/total_to_process_session:.2f}%). "
                                  f"Last: {title_id} -> Date: {date_str if date_str else 'None'}, Status: {status_str}. "
                                  f"Elapsed: {time.strftime('%H:%M:%S', time.gmtime(elapsed_time_session))}. ETA: {eta_str}")
                    
                    print(f"\nSaving intermediate results after chunk. Processed {processed_count_session} so far in this session.")
                    df_original.to_parquet(OUTPUT_FILE_WITH_DATES, index=False)
                    print(f"DataFrame snapshot saved to {OUTPUT_FILE_WITH_DATES}")

            except KeyboardInterrupt:
                print("\nProcess interrupted by user. Shutting down workers and attempting to save final progress...")
                if 'pool' in locals() and hasattr(pool, '_state') and pool._state == multiprocessing.pool.RUN:
                    pool.terminate() 
                    pool.join()      
            except Exception as e_main: # Catch other exceptions in the main loop
                print(f"CRITICAL ERROR in main processing loop: {e_main}")
                if 'pool' in locals() and hasattr(pool, '_state') and pool._state == multiprocessing.pool.RUN:
                    pool.terminate()
                    pool.join()
            
        print("\nFinished fetching all designated titles for this session.")
        df_original.to_parquet(OUTPUT_FILE_WITH_DATES, index=False)
        print(f"Final data for this session saved to {OUTPUT_FILE_WITH_DATES}")

    # --- Analysis Part ---
    print("\n--- Analysis of Results ---")
    if not os.path.exists(OUTPUT_FILE_WITH_DATES):
        print(f"Output file {OUTPUT_FILE_WITH_DATES} not found. Cannot perform analysis.")
    else:
        df_results_final = pd.read_parquet(OUTPUT_FILE_WITH_DATES)
        print(f"Loaded {len(df_results_final)} records from the output file for analysis.")

        if 'fetch_status' in df_results_final.columns:
            print("\nFetch Status Summary:")
            print(df_results_final['fetch_status'].value_counts(dropna=False).to_string())
        else:
            print("Column 'fetch_status' not found in results. Cannot provide status summary.")

        successful_mask = (df_results_final['fetch_status'] == "SUCCESS") & df_results_final['release_date_full'].notna()
        successful_df_final = df_results_final[successful_mask].copy()
        
        print(f"\nNumber of records with 'SUCCESS' status and a non-NA date: {len(successful_df_final)}")

        if not successful_df_final.empty:
            successful_df_final['release_date_full'] = pd.to_datetime(successful_df_final['release_date_full'], errors='coerce')
            successful_df_final.dropna(subset=['release_date_full'], inplace=True)
            print(f"Number of records with valid datetime objects after conversion: {len(successful_df_final)}")

            if not successful_df_final.empty:
                successful_df_final['release_week'] = successful_df_final['release_date_full'].dt.isocalendar().week
                print("\nSample of data with release week:")
                display_cols = ['title_id', 'release_date_full', 'release_week']
                if 'title' in successful_df_final.columns: display_cols.insert(1, 'title')
                print(successful_df_final[display_cols].head().to_string())
                
                if 'genre' in successful_df_final.columns:
                    successful_df_final['genre'] = successful_df_final['genre'].astype(str) 
                    target_genre_for_analysis = 'Action' 
                    genre_specific_movies = successful_df_final[successful_df_final['genre'].str.contains(target_genre_for_analysis, na=False, case=False)]
                    if not genre_specific_movies.empty:
                        weekly_counts_specific_genre = genre_specific_movies.groupby('release_week').size()
                        print(f"\nWeekly counts for '{target_genre_for_analysis}' movies (sample from successful fetches):")
                        print(weekly_counts_specific_genre.head().to_string())
                    else:
                        print(f"No '{target_genre_for_analysis}' movies found among successful fetches with genre data.")
                else:
                    print("Column 'genre' not found in successful_df_final. Skipping genre-specific analysis.")
            else:
                print("No records remained after attempting to convert release_date_full to datetime.")
        else:
            print("No records had 'SUCCESS' status with a non-NA date, or all failed date conversion.")