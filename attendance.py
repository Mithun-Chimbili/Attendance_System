"""
Attendance Reporting and Utilities Module

Provides utilities for:
- Attendance reporting
- User management
- System statistics
- Data export and analysis
"""

import pandas as pd
import os
from datetime import datetime, timedelta
from pathlib import Path

ENCODING_PATH = "encodings"
ATTENDANCE_FILE = "attendance.csv"

class AttendanceReport:
    """Generates attendance reports and statistics."""
    
    def __init__(self):
        self.attendance_df = None
        self.load_data()
    
    def load_data(self):
        """Load attendance data from CSV."""
        if os.path.exists(ATTENDANCE_FILE):
            self.attendance_df = pd.read_csv(ATTENDANCE_FILE)
        else:
            self.attendance_df = pd.DataFrame(columns=["Name", "Date", "Punch_In", "Punch_Out", "Confidence", "Liveness_Check"])
    
    def get_daily_report(self, date=None):
        """Get attendance report for a specific date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        daily_df = self.attendance_df[self.attendance_df["Date"] == date]
        
        print("\n" + "="*70)
        print(f"ATTENDANCE REPORT - {date}")
        print("="*70)
        
        if daily_df.empty:
            print("No attendance records for this date.")
        else:
            for idx, row in daily_df.iterrows():
                punch_in = row["Punch_In"] if pd.notna(row["Punch_In"]) else "N/A"
                punch_out = row["Punch_Out"] if pd.notna(row["Punch_Out"]) and row["Punch_Out"] != "" else "Not marked"
                print(f"\n{row['Name']}")
                print(f"  Punch In:  {punch_in}")
                print(f"  Punch Out: {punch_out}")
                if pd.notna(row.get("Confidence")):
                    print(f"  Confidence: {row['Confidence']}")
                if pd.notna(row.get("Liveness_Check")):
                    print(f"  Liveness: {row['Liveness_Check']}")
        
        print("\n" + "="*70 + "\n")
    
    def get_user_history(self, name, days=30):
        """Get attendance history for a user."""
        user_df = self.attendance_df[self.attendance_df["Name"] == name]
        
        print("\n" + "="*70)
        print(f"ATTENDANCE HISTORY - {name} (Last {days} days)")
        print("="*70)
        
        if user_df.empty:
            print(f"No attendance records for {name}.")
        else:
            # Calculate working hours
            user_df = user_df.copy()
            user_df["Date"] = pd.to_datetime(user_df["Date"])
            user_df = user_df[user_df["Date"] >= datetime.now() - timedelta(days=days)]
            
            for idx, row in user_df.iterrows():
                punch_in = row["Punch_In"]
                punch_out = row["Punch_Out"] if pd.notna(row["Punch_Out"]) and row["Punch_Out"] != "" else "Not marked"
                
                # Calculate duration
                if punch_out != "Not marked":
                    try:
                        in_time = datetime.strptime(punch_in, "%H:%M:%S")
                        out_time = datetime.strptime(punch_out, "%H:%M:%S")
                        duration = out_time - in_time
                        hours = duration.total_seconds() / 3600
                        print(f"\n{row['Date'].strftime('%Y-%m-%d')}")
                        print(f"  Punch In:  {punch_in}")
                        print(f"  Punch Out: {punch_out}")
                        print(f"  Duration:  {hours:.2f} hours")
                    except:
                        print(f"\n{row['Date'].strftime('%Y-%m-%d')}")
                        print(f"  Punch In:  {punch_in}")
                        print(f"  Punch Out: {punch_out}")
                else:
                    print(f"\n{row['Date'].strftime('%Y-%m-%d')}")
                    print(f"  Punch In:  {punch_in}")
                    print(f"  Punch Out: {punch_out}")
        
        print("\n" + "="*70 + "\n")
    
    def get_summary_stats(self):
        """Get overall system statistics."""
        print("\n" + "="*70)
        print("SYSTEM STATISTICS")
        print("="*70)
        
        # Count registered users
        registered_users = []
        if os.path.exists(ENCODING_PATH):
            for file in os.listdir(ENCODING_PATH):
                if file.endswith(".npy"):
                    registered_users.append(file.replace(".npy", ""))
        
        print(f"\nRegistered Users: {len(registered_users)}")
        if registered_users:
            for user in registered_users:
                print(f"  • {user}")
        
        # Attendance statistics
        if not self.attendance_df.empty:
            total_records = len(self.attendance_df)
            unique_users = self.attendance_df["Name"].nunique()
            unique_dates = self.attendance_df["Date"].nunique()
            
            print(f"\nAttendance Records: {total_records}")
            print(f"Unique Users Marked: {unique_users}")
            print(f"Dates with Records: {unique_dates}")
            
            # Liveness verification stats
            if "Liveness_Check" in self.attendance_df.columns:
                verified = (self.attendance_df["Liveness_Check"] == "VERIFIED").sum()
                print(f"Liveness Verified: {verified}/{total_records}")
        
        print("\n" + "="*70 + "\n")
    
    def export_report(self, filename="attendance_report.csv"):
        """Export attendance data to CSV."""
        if self.attendance_df.empty:
            print("No attendance data to export.")
            return
        
        self.attendance_df.to_csv(filename, index=False)
        print(f"✅ Report exported to {filename}")

class UserManager:
    """Manages registered users."""
    
    @staticmethod
    def list_users():
        """List all registered users."""
        print("\n" + "="*70)
        print("REGISTERED USERS")
        print("="*70)
        
        users = []
        if os.path.exists(ENCODING_PATH):
            for file in os.listdir(ENCODING_PATH):
                if file.endswith(".npy"):
                    user_name = file.replace(".npy", "")
                    file_path = os.path.join(ENCODING_PATH, file)
                    file_size = os.path.getsize(file_path)
                    users.append((user_name, file_size))
        
        if not users:
            print("No registered users found.")
        else:
            for user_name, file_size in sorted(users):
                print(f"  • {user_name} ({file_size} bytes)")
        
        print("="*70 + "\n")
        return users
    
    @staticmethod
    def delete_user(user_name):
        """Delete a registered user."""
        file_path = f"{ENCODING_PATH}/{user_name}.npy"
        
        if not os.path.exists(file_path):
            print(f"❌ User '{user_name}' not found.")
            return False
        
        confirmation = input(f"⚠ Delete '{user_name}'? This cannot be undone. (yes/no): ")
        
        if confirmation.lower() == "yes":
            os.remove(file_path)
            print(f"✅ User '{user_name}' deleted.")
            return True
        else:
            print("Deletion cancelled.")
            return False
    
    @staticmethod
    def export_users_list(filename="registered_users.txt"):
        """Export list of registered users."""
        users = []
        if os.path.exists(ENCODING_PATH):
            for file in os.listdir(ENCODING_PATH):
                if file.endswith(".npy"):
                    users.append(file.replace(".npy", ""))
        
        if not users:
            print("No users to export.")
            return
        
        with open(filename, "w") as f:
            f.write("REGISTERED USERS\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            for user in sorted(users):
                f.write(f"{user}\n")
        
        print(f"✅ Users list exported to {filename}")

def main_menu():
    """Interactive menu for attendance management."""
    print("\n" + "="*70)
    print("ATTENDANCE MANAGEMENT SYSTEM")
    print("="*70)
    print("\nOptions:")
    print("  1. View daily attendance report")
    print("  2. View user attendance history")
    print("  3. View system statistics")
    print("  4. List registered users")
    print("  5. Delete a user")
    print("  6. Export attendance report")
    print("  7. Export users list")
    print("  0. Exit")
    print("-"*70)
    
    choice = input("Select option (0-7): ").strip()
    
    if choice == "1":
        date_input = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
        report = AttendanceReport()
        report.get_daily_report(date_input if date_input else None)
    
    elif choice == "2":
        name = input("Enter user name: ").strip()
        days = input("Enter number of days to check (default: 30): ").strip()
        report = AttendanceReport()
        report.get_user_history(name, int(days) if days else 30)
    
    elif choice == "3":
        report = AttendanceReport()
        report.get_summary_stats()
    
    elif choice == "4":
        UserManager.list_users()
    
    elif choice == "5":
        UserManager.list_users()
        name = input("Enter user name to delete: ").strip()
        UserManager.delete_user(name)
    
    elif choice == "6":
        filename = input("Enter filename (default: attendance_report.csv): ").strip()
        report = AttendanceReport()
        report.export_report(filename if filename else "attendance_report.csv")
    
    elif choice == "7":
        filename = input("Enter filename (default: registered_users.txt): ").strip()
        UserManager.export_users_list(filename if filename else "registered_users.txt")
    
    elif choice == "0":
        print("Exiting...")
        return False
    
    else:
        print("Invalid option. Please try again.")
    
    return True

if __name__ == "__main__":
    try:
        while main_menu():
            continue
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
