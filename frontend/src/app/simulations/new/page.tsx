'use client';

import { Suspense } from 'react';
import { ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StepWizard } from '@/components/ui/StepWizard';
import {
  useSimulationWizard,
  PlaybookFromQuerySync,
  PlaybookSelect,
  ConfigureAgents,
  SeedDocuments,
  ObjectiveStep,
  EngineSettings,
  ReviewLaunch,
} from '@/components/simulation/wizard';

export default function NewSimulationPage() {
  const w = useSimulationWizard();
  const nextDisabled = !w.canProceed();

  return (
    <div className="space-y-4 sm:space-y-6 animate-fade-in max-w-5xl mx-auto">
      <Suspense fallback={null}>
        <PlaybookFromQuerySync
          playbooks={w.playbooks}
          setSelectedPlaybook={w.setSelectedPlaybook}
        />
      </Suspense>

      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">New Simulation</h1>
        <p className="text-foreground-muted mt-1 text-sm sm:text-base">
          Configure your war-gaming scenario step by step
        </p>
      </div>

      {w.showDraftBanner && (
        <Card padding="md" className="border-accent/30 bg-accent/5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p className="text-sm text-foreground">
              You have a saved draft for this simulation wizard.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" size="sm" onClick={w.resumeDraft}>
                Resume draft
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={w.discardDraft}>
                Start over
              </Button>
            </div>
          </div>
        </Card>
      )}

      <Card padding="lg">
        <StepWizard
          steps={w.steps}
          currentStep={w.currentStep}
          maxVisitedStep={w.maxVisitedStep}
          onStepClick={w.setCurrentStep}
        />
      </Card>

      <Card padding="lg">
        {w.currentStep === 0 && (
          <PlaybookSelect
            playbooks={w.playbooks}
            selectedPlaybook={w.selectedPlaybook}
            setSelectedPlaybook={w.setSelectedPlaybook}
            playbookDetailLoading={w.playbookDetailLoading}
            playbookDetailError={w.playbookDetailError}
            retryPlaybookDetail={w.retryPlaybookDetail}
          />
        )}

        {w.currentStep === 1 && w.selectedPlaybook && (
          <ConfigureAgents
            selectedPlaybook={w.selectedPlaybook}
            agentConfigs={w.agentConfigs}
            updateAgentCount={w.updateAgentCount}
            totalAgents={w.totalAgents}
          />
        )}

        {w.currentStep === 2 && (
          <SeedDocuments
            uploadedFiles={w.uploadedFiles}
            selectedSeedIds={w.selectedSeedIds}
            toggleSeedId={w.toggleSeedId}
            handleFilesDrop={w.handleFilesDrop}
          />
        )}

        {w.currentStep === 3 && <ObjectiveStep w={w} />}

        {w.currentStep === 4 && <EngineSettings w={w} />}

        {w.currentStep === 5 && w.selectedPlaybook && (
          <ReviewLaunch
            selectedPlaybook={w.selectedPlaybook}
            staleSavedModelId={w.staleSavedModelId}
            setModelSelection={w.setModelSelection}
            simulationName={w.simulationName}
            simulationObjective={w.simulationObjective}
            enrichResearch={w.enrichResearch}
            evidencePackCount={w.evidencePacks.length}
            rounds={w.rounds}
            environmentType={w.environmentType}
            modelSelectionLabel={w.modelSelectionLabel}
            totalAgents={w.totalAgents}
            selectedSeedIds={w.selectedSeedIds}
            effectiveMonteCarloIterations={w.effectiveMonteCarloIterations}
            includePostRunReport={w.includePostRunReport}
            includePostRunAnalytics={w.includePostRunAnalytics}
            extendedSeedContext={w.extendedSeedContext}
            agentConfigs={w.agentConfigs}
            estimateLoading={w.estimateLoading}
            estimateFailed={w.estimateFailed}
            costEstimate={w.costEstimate}
            wizardLlmProvider={w.wizardLlmProvider}
            onEditStep={w.setCurrentStep}
          />
        )}
      </Card>

      <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3">
        <Button
          variant="ghost"
          onClick={w.handleBack}
          disabled={w.currentStep === 0}
          leftIcon={<ChevronLeft className="w-4 h-4" />}
          className="w-full sm:w-auto"
        >
          Back
        </Button>
        <div className="flex flex-col items-stretch sm:items-end gap-2 w-full sm:w-auto">
          {nextDisabled && w.canProceedReason && (
            <p className="text-sm text-foreground-muted text-center sm:text-right" role="status">
              {w.canProceedReason}
            </p>
          )}
          {w.currentStep < w.steps.length - 1 ? (
            <Button
              onClick={w.handleNext}
              disabled={nextDisabled}
              rightIcon={<ChevronRight className="w-4 h-4" />}
              className="w-full sm:w-auto"
            >
              Next
            </Button>
          ) : (
            <Button
              onClick={w.handleLaunch}
              disabled={nextDisabled || w.isLoading}
              isLoading={w.isLoading}
              leftIcon={!w.isLoading ? <Check className="w-4 h-4" /> : undefined}
              className="w-full sm:w-auto"
            >
              Launch Simulation
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
