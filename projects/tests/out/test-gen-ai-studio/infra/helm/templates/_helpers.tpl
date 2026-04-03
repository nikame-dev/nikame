{/* Common labels */}
{{- define "gen-ai-studio.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: gen-ai-studio
{{- end }}
