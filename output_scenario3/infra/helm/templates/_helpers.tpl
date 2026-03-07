{/* Common labels */}
{{- define "test-full-saas.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: test-full-saas
{{- end }}
