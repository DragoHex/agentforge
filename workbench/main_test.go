package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestMain creates mock shell scripts so handler tests don't hit the real file-system.
func TestMain(m *testing.M) {
	tmpDir, err := os.MkdirTemp("", "wb-server-test-*")
	if err != nil {
		panic("cannot create tmp dir: " + err.Error())
	}

	for _, name := range []string{"update-all.sh", "fetch-jira-detail.sh", "transition-ticket.sh"} {
		body := "#!/usr/bin/env bash\necho \"mock:" + name + " args=$*\"\n"
		if err := os.WriteFile(filepath.Join(tmpDir, name), []byte(body), 0755); err != nil {
			panic("cannot write mock script: " + err.Error())
		}
	}

	scriptsDir = tmpDir
	code := m.Run()
	os.RemoveAll(tmpDir)
	os.Exit(code)
}

// ─── helpers ─────────────────────────────────────────────────────────────────

func decodeJSON(t *testing.T, w *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var m map[string]any
	if err := json.NewDecoder(w.Body).Decode(&m); err != nil {
		t.Fatalf("cannot decode JSON body: %v\nbody: %s", err, w.Body.String())
	}
	return m
}

func assertStatus(t *testing.T, w *httptest.ResponseRecorder, want int) {
	t.Helper()
	if w.Code != want {
		t.Errorf("HTTP status: want %d, got %d\nbody: %s", want, w.Code, w.Body.String())
	}
}

func assertCORS(t *testing.T, w *httptest.ResponseRecorder) {
	t.Helper()
	if got := w.Header().Get("Access-Control-Allow-Origin"); got != "*" {
		t.Errorf("CORS Allow-Origin: want *, got %q", got)
	}
	if got := w.Header().Get("Access-Control-Allow-Methods"); !strings.Contains(got, "POST") {
		t.Errorf("CORS Allow-Methods should include POST, got %q", got)
	}
}

// ─── GET /status ─────────────────────────────────────────────────────────────

func TestHandleStatus_ReturnsOK(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/status", nil)
	w := httptest.NewRecorder()
	handleStatus(w, req)

	assertStatus(t, w, http.StatusOK)
	body := decodeJSON(t, w)
	if v, _ := body["ok"].(bool); !v {
		t.Errorf("expected ok:true, got %v", body["ok"])
	}
}

func TestHandleStatus_HasCORSHeaders(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/status", nil)
	w := httptest.NewRecorder()
	handleStatus(w, req)
	assertCORS(t, w)
}

func TestHandleStatus_PreflightReturns204(t *testing.T) {
	req := httptest.NewRequest(http.MethodOptions, "/status", nil)
	w := httptest.NewRecorder()
	handleStatus(w, req)
	assertStatus(t, w, http.StatusNoContent)
}

// ─── POST /refresh ────────────────────────────────────────────────────────────

func TestHandleRefresh_WrongMethodReturns405(t *testing.T) {
	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		t.Run(method, func(t *testing.T) {
			req := httptest.NewRequest(method, "/refresh", nil)
			w := httptest.NewRecorder()
			handleRefresh(w, req)
			assertStatus(t, w, http.StatusMethodNotAllowed)
		})
	}
}

func TestHandleRefresh_PreflightReturns204(t *testing.T) {
	req := httptest.NewRequest(http.MethodOptions, "/refresh", nil)
	w := httptest.NewRecorder()
	handleRefresh(w, req)
	assertStatus(t, w, http.StatusNoContent)
}

func TestHandleRefresh_RunsMockScript(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/refresh", nil)
	w := httptest.NewRecorder()
	handleRefresh(w, req)

	assertStatus(t, w, http.StatusOK)
	body := decodeJSON(t, w)
	if _, has := body["ok"]; !has {
		t.Error("response missing 'ok' field")
	}
	if _, has := body["output"]; !has {
		t.Error("response missing 'output' field")
	}
	// Mock script echoes "mock:update-all.sh"; ok should be true
	if v, _ := body["ok"].(bool); !v {
		t.Errorf("expected ok:true from mock script, got %v", body["ok"])
	}
}

func TestHandleRefresh_ScriptFailureReturnsOkFalse(t *testing.T) {
	failDir, _ := os.MkdirTemp("", "wb-fail-*")
	defer os.RemoveAll(failDir)
	os.WriteFile(filepath.Join(failDir, "update-all.sh"),
		[]byte("#!/usr/bin/env bash\necho 'ERROR: mock'\nexit 1\n"), 0755)

	orig := scriptsDir
	scriptsDir = failDir
	defer func() { scriptsDir = orig }()

	req := httptest.NewRequest(http.MethodPost, "/refresh", nil)
	w := httptest.NewRecorder()
	handleRefresh(w, req)

	assertStatus(t, w, http.StatusOK) // always 200; ok:false signals failure
	body := decodeJSON(t, w)
	if v, _ := body["ok"].(bool); v {
		t.Error("expected ok:false for failing script")
	}
}

// ─── POST /fetch-ticket ───────────────────────────────────────────────────────

func TestHandleFetchTicket_MissingJiraIDReturns400(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/fetch-ticket", nil)
	w := httptest.NewRecorder()
	handleFetchTicket(w, req)
	assertStatus(t, w, http.StatusBadRequest)
}

func TestHandleFetchTicket_WrongMethodReturns405(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/fetch-ticket?jira_id=AV-1", nil)
	w := httptest.NewRecorder()
	handleFetchTicket(w, req)
	assertStatus(t, w, http.StatusMethodNotAllowed)
}

func TestHandleFetchTicket_PreflightReturns204(t *testing.T) {
	req := httptest.NewRequest(http.MethodOptions, "/fetch-ticket?jira_id=AV-1", nil)
	w := httptest.NewRecorder()
	handleFetchTicket(w, req)
	assertStatus(t, w, http.StatusNoContent)
}

func TestHandleFetchTicket_ValidIDRunsScript(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/fetch-ticket?jira_id=AV-1234", nil)
	w := httptest.NewRecorder()
	handleFetchTicket(w, req)

	assertStatus(t, w, http.StatusOK)
	body := decodeJSON(t, w)
	if out, _ := body["output"].(string); !strings.Contains(out, "AV-1234") {
		t.Errorf("expected output to contain ticket id, got %q", out)
	}
}

func TestHandleFetchTicket_WorktreeParamPassedToScript(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/fetch-ticket?jira_id=AV-5&worktree=my-wt", nil)
	w := httptest.NewRecorder()
	handleFetchTicket(w, req)

	assertStatus(t, w, http.StatusOK)
	body := decodeJSON(t, w)
	out, _ := body["output"].(string)
	if !strings.Contains(out, "my-wt") {
		t.Errorf("expected worktree in script args, got output: %q", out)
	}
}

// ─── POST /transition-ticket ─────────────────────────────────────────────────

func TestHandleTransitionTicket_MissingBothParamsReturns400(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/transition-ticket", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)

	assertStatus(t, w, http.StatusBadRequest)
	body := decodeJSON(t, w)
	if msg, _ := body["error"].(string); msg == "" {
		t.Error("expected non-empty error message")
	}
}

func TestHandleTransitionTicket_MissingTicketIDReturns400(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/transition-ticket?target_status=in_progress", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)
	assertStatus(t, w, http.StatusBadRequest)
}

func TestHandleTransitionTicket_MissingTargetStatusReturns400(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/transition-ticket?ticket_id=AV-1234", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)
	assertStatus(t, w, http.StatusBadRequest)
}

func TestHandleTransitionTicket_WrongMethodReturns405(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/transition-ticket?ticket_id=AV-1&target_status=todo", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)
	assertStatus(t, w, http.StatusMethodNotAllowed)
}

func TestHandleTransitionTicket_PreflightReturns204(t *testing.T) {
	req := httptest.NewRequest(http.MethodOptions, "/transition-ticket", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)
	assertStatus(t, w, http.StatusNoContent)
}

func TestHandleTransitionTicket_RunsMockScript(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/transition-ticket?ticket_id=AV-9999&target_status=in_progress", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)

	assertStatus(t, w, http.StatusOK)
	body := decodeJSON(t, w)
	if v, _ := body["ok"].(bool); !v {
		t.Errorf("expected ok:true from mock script, got %v (output: %v)", body["ok"], body["output"])
	}
	out, _ := body["output"].(string)
	if !strings.Contains(out, "AV-9999") {
		t.Errorf("expected ticket id in script output, got %q", out)
	}
	if !strings.Contains(out, "in_progress") {
		t.Errorf("expected target_status in script output, got %q", out)
	}
}

func TestHandleTransitionTicket_ScriptFailureReturnsOkFalse(t *testing.T) {
	failDir, _ := os.MkdirTemp("", "wb-fail-*")
	defer os.RemoveAll(failDir)
	os.WriteFile(filepath.Join(failDir, "transition-ticket.sh"),
		[]byte("#!/usr/bin/env bash\necho 'ERROR: Jira refused'\nexit 1\n"), 0755)

	orig := scriptsDir
	scriptsDir = failDir
	defer func() { scriptsDir = orig }()

	req := httptest.NewRequest(http.MethodPost, "/transition-ticket?ticket_id=AV-1&target_status=done", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)

	assertStatus(t, w, http.StatusOK) // HTTP 200 always; ok:false encodes failure
	body := decodeJSON(t, w)
	if v, _ := body["ok"].(bool); v {
		t.Error("expected ok:false for failing script")
	}
	if out, _ := body["output"].(string); !strings.Contains(out, "ERROR") {
		t.Errorf("expected ERROR in output, got %q", out)
	}
}

func TestHandleTransitionTicket_HasCORSHeaders(t *testing.T) {
	req := httptest.NewRequest(http.MethodPost, "/transition-ticket?ticket_id=AV-1&target_status=todo", nil)
	w := httptest.NewRecorder()
	handleTransitionTicket(w, req)
	assertCORS(t, w)
}

// ─── runScript ────────────────────────────────────────────────────────────────

func TestRunScript_SuccessfulCommand(t *testing.T) {
	out, ok := runScript([]string{"bash", "-c", "echo hello"})
	if !ok {
		t.Error("expected ok:true for echo command")
	}
	if !strings.Contains(out, "hello") {
		t.Errorf("expected 'hello' in output, got %q", out)
	}
}

func TestRunScript_FailingCommand(t *testing.T) {
	_, ok := runScript([]string{"bash", "-c", "exit 1"})
	if ok {
		t.Error("expected ok:false for failing command")
	}
}

func TestRunScript_OutputTruncatedAt4000Chars(t *testing.T) {
	// Generate > 4000 chars
	out, ok := runScript([]string{"bash", "-c", "printf 'x%.0s' {1..5000}"})
	if !ok {
		t.Fatal("expected ok:true")
	}
	if len(out) > 4000 {
		t.Errorf("output should be capped at 4000 chars, got %d", len(out))
	}
}
