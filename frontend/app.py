import streamlit as st
from utils import (
    create_task, list_tasks, update_task, delete_task,
    transcribe_video, generate_tasks_from_transcript
)

def main():
    st.title("Streamlit + Supabase + OpenAI (MP4 Analysis)")

    st.header("1. Upload MP4 to Transcribe and Generate Tasks")
    video_file = st.file_uploader("Upload an .mp4 file", type=["mp4"])

    if "selected_tasks" not in st.session_state:
        st.session_state.tasks_list = []

    if "transcript" not in st.session_state:
        st.session_state.transcript = ""

    if "tasks_list" not in st.session_state:
        st.session_state.tasks_list = []

    if "selected_tasks" not in st.session_state:
        st.session_state.selected_tasks = []

    if video_file:
        if st.button("Transcribe and Generate Tasks"):
            with st.spinner("Transcribing and generating tasks..."):
                st.session_state.transcript = transcribe_video(video_file.getvalue())
                st.success("Transcription done!")
                st.subheader("Transcript:")
                with st.expander("See full transcript"):
                    st.write(st.session_state.transcript)

                st.session_state.tasks_list = generate_tasks_from_transcript(st.session_state.transcript)
                st.subheader("Generated Tasks:")

    if st.session_state.tasks_list:
        for t in st.session_state.tasks_list:
            st.write(f"- {t}")
        
        st.session_state.selected_tasks = st.multiselect(
            "Select which tasks to add to the database:",
            st.session_state.tasks_list
        )

        if st.button("Add Selected Tasks to Supabase"):
            if st.session_state.selected_tasks:
                for t in st.session_state.selected_tasks:
                    create_task(t)
                st.success("Selected tasks have been saved to Supabase!")
            else:
                st.warning("No tasks selected.")
    else:
        st.info("No tasks identified from the transcript.")

    st.header("2. List Tasks from Supabase")
    if st.button("Refresh Task List"):
        resp = list_tasks()
        if resp.data:
            st.write("**Tasks in Supabase:**")
            for item in resp.data:
                st.write(f"ID: {item['id']} - {item['description']}")
        else:
            st.info("No tasks found in Supabase.")

    st.header("3. Update Task")
    task_id_to_update = st.number_input("Task ID to update", min_value=1, step=1)
    new_description = st.text_input("New Task Description")
    if st.button("Update Task"):
        if new_description.strip():
            resp = update_task(task_id_to_update, new_description.strip())
            if resp.error:
                st.error(f"Error updating: {resp.error}")
            else:
                st.success("Task updated successfully.")
        else:
            st.warning("Please enter a new description.")

    st.header("4. Delete Task")
    task_id_to_delete = st.number_input("Task ID to delete", min_value=1, step=1)
    if st.button("Delete Task"):
        resp = delete_task(task_id_to_delete)
        if resp.error:
            st.error(f"Error deleting: {resp.error}")
        else:
            st.success("Task deleted successfully.")

if __name__ == "__main__":
    main()
