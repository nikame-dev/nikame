{/* Common labels */}
{{- define "custom-hybrid-db.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: custom-hybrid-db
{{- end }}
