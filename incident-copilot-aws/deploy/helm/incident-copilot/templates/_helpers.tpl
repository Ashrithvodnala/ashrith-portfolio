{{- define "copilot.labels" -}}
app.kubernetes.io/name: incident-copilot
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end -}}
{{- define "copilot.selector" -}}
app.kubernetes.io/name: incident-copilot
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
