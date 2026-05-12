package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
)

const port = ":1337"

// scriptsDir is resolved relative to this binary's location.
var scriptsDir string

func init() {
	exe, err := os.Executable()
	if err != nil {
		log.Fatalf("cannot resolve executable path: %v", err)
	}
	// Binary lives in server/, scripts live one level up in scripts/
	scriptsDir = filepath.Join(filepath.Dir(exe), "..", "scripts")
}

func cors(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "*")
	w.Header().Set("Content-Type", "application/json")
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	cors(w)
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

func runScript(args []string) (string, bool) {
	cmd := exec.Command(args[0], args[1:]...)
	out, err := cmd.CombinedOutput()
	output := string(out)
	if len(output) > 4000 {
		output = output[len(output)-4000:]
	}
	return output, err == nil
}

func preflight(w http.ResponseWriter, r *http.Request) bool {
	if r.Method == http.MethodOptions {
		cors(w)
		w.WriteHeader(http.StatusNoContent)
		return true
	}
	return false
}

// GET /status
func handleStatus(w http.ResponseWriter, r *http.Request) {
	if preflight(w, r) {
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

// POST /refresh  — runs update-all.sh
func handleRefresh(w http.ResponseWriter, r *http.Request) {
	if preflight(w, r) {
		return
	}
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST required"})
		return
	}
	script := filepath.Join(scriptsDir, "update-all.sh")
	output, ok := runScript([]string{"bash", script})
	writeJSON(w, http.StatusOK, map[string]any{"ok": ok, "output": output})
}

// POST /fetch-ticket?jira_id=AV-XXXXX[&worktree=name]  — runs fetch-jira-detail.sh
func handleFetchTicket(w http.ResponseWriter, r *http.Request) {
	if preflight(w, r) {
		return
	}
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "POST required"})
		return
	}

	jiraID := r.URL.Query().Get("jira_id")
	worktree := r.URL.Query().Get("worktree")

	if jiraID == "" {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "jira_id query param required"})
		return
	}

	script := filepath.Join(scriptsDir, "fetch-jira-detail.sh")
	args := []string{"bash", script, jiraID}
	if worktree != "" {
		args = append(args, "--worktree", worktree)
	}

	output, ok := runScript(args)
	writeJSON(w, http.StatusOK, map[string]any{"ok": ok, "output": output})
}

func main() {
	http.HandleFunc("/status", handleStatus)
	http.HandleFunc("/refresh", handleRefresh)
	http.HandleFunc("/fetch-ticket", handleFetchTicket)

	log.Printf("Workbench server listening on http://127.0.0.1%s", port)
	if err := http.ListenAndServe("127.0.0.1"+port, nil); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
