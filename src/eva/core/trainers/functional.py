"""Fit session related functions."""

from typing import Tuple

from lightning.pytorch.utilities.types import _EVALUATE_OUTPUT

from eva.core.data import datamodules
from eva.core.models import modules
from eva.core.trainers import _recorder, _utils
from eva.core.trainers import trainer as eva_trainer


def run_evaluation_session(
    base_trainer: eva_trainer.Trainer,
    base_model: modules.ModelModule,
    datamodule: datamodules.DataModule,
    *,
    n_runs: int = 1,
    verbose: bool = True,
) -> None:
    """Runs a downstream evaluation session out-of-place.

    It performs an evaluation run (fit and evaluate) on the model
    multiple times. Note that as the input `base_trainer` and
    `base_model` would be cloned, the input object would not
    be modified.

    Args:
        base_trainer: The base trainer module to use.
        base_model: The base model module to use.
        datamodule: The data module.
        n_runs: The amount of runs (fit and evaluate) to perform.
        verbose: Whether to verbose the session metrics instead of
            these of each individual runs and vice-versa.
    """
    recorder = _recorder.SessionRecorder(output_dir=base_trainer.default_log_dir, verbose=verbose)
    for run_index in range(n_runs):
        validation_scores, test_scores = run_evaluation(
            base_trainer,
            base_model,
            datamodule,
            run_id=run_index,
            verbose=not verbose,
        )
        recorder.update(validation_scores, test_scores)
    recorder.save()


def run_evaluation(
    base_trainer: eva_trainer.Trainer,
    base_model: modules.ModelModule,
    datamodule: datamodules.DataModule,
    *,
    run_id: int | None = None,
    verbose: bool = True,
) -> Tuple[_EVALUATE_OUTPUT, _EVALUATE_OUTPUT | None]:
    """Fits and evaluates a model out-of-place.

    Args:
        base_trainer: The base trainer to use but not modify.
        base_model: The model module to use but not modify.
        datamodule: The data module.
        run_id: The run id to be appended to the output log directory.
        verbose: Whether to print the validation and test metrics
            in the end of the training.

    Returns:
        A tuple of with the validation and the test metrics (if exists).
    """
    trainer, model = _utils.clone(base_trainer, base_model)
    model.configure_model()

    trainer.init_logger_run(run_id)
    results = fit_and_validate(trainer, model, datamodule, verbose=verbose)
    trainer.finish_logger_run(run_id)

    return results


def fit_and_validate(
    trainer: eva_trainer.Trainer,
    model: modules.ModelModule,
    datamodule: datamodules.DataModule,
    verbose: bool = True,
) -> Tuple[_EVALUATE_OUTPUT, _EVALUATE_OUTPUT | None]:
    """Fits and evaluates a model in-place.

    If the test set is set in the datamodule, it will evaluate the model
    on the test set as well.

    Args:
        trainer: The trainer module to use and update in-place.
        model: The model module to use and update in-place.
        datamodule: The data module.
        verbose: Whether to print the validation and test metrics
            in the end of the training.

    Returns:
        A tuple of with the validation and the test metrics (if exists).
    """
    trainer.fit(model, datamodule=datamodule)
    validation_scores = trainer.validate(
        datamodule=datamodule, verbose=verbose, ckpt_path=trainer.checkpoint_type
    )
    test_scores = (
        None
        if datamodule.datasets.test is None
        else trainer.test(datamodule=datamodule, verbose=verbose, ckpt_path=trainer.checkpoint_type)
    )
    return validation_scores, test_scores


def infer_model(
    base_trainer: eva_trainer.Trainer,
    base_model: modules.ModelModule,
    datamodule: datamodules.DataModule,
    *,
    return_predictions: bool = False,
) -> None:
    """Performs model inference out-of-place.

    Note that the input `base_model` and `base_trainer` would
    not be modified.

    Args:
        base_trainer: The base trainer to use but not modify.
        base_model: The model module to use but not modify.
        datamodule: The data module.
        return_predictions: Whether to return the model predictions.
    """
    trainer, model = _utils.clone(base_trainer, base_model)
    return trainer.predict(
        model=model,
        datamodule=datamodule,
        return_predictions=return_predictions,
    )
